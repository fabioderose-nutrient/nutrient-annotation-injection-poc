// Annotation injection PoC frontend. The sidebar is a plain JSON editor: pick
// or edit the LLM output, hit "Process LLM output", and the server
// re-resolves and re-injects every annotation. Clicking a result jumps to the
// highlight.

let instance = null;

// Default mode is server-backed: the viewer connects to Document Engine and
// annotations live server-side only, synced to the browser via Instant. Add
// ?mode=standalone to the URL to render locally via WebAssembly instead (the
// annotations are then fetched once as Instant JSON).
const SERVER_MODE = new URLSearchParams(location.search).get("mode") !== "standalone";

async function loadViewer() {
  if (instance) {
    PSPDFKit.unload("#viewer");
    instance = null;
  }
  if (SERVER_MODE) {
    const config = await fetch("/api/viewer-config").then((r) => r.json());
    instance = await PSPDFKit.load({
      container: "#viewer",
      serverUrl: config.serverUrl,
      documentId: config.documentId,
      authPayload: { jwt: config.jwt },
      instant: true,
      licenseKey: config.licenseKey || undefined,
    });
    return;
  }
  const [config, instantJSON] = await Promise.all([
    fetch("/api/viewer-config").then((r) => r.json()),
    fetch("/api/instant-json").then((r) => r.json()),
  ]);
  instance = await PSPDFKit.load({
    container: "#viewer",
    document: "/api/document.pdf",
    licenseKey: config.licenseKey || undefined,
    instantJSON: instantJSON.annotations.length ? instantJSON : undefined,
  });
}

function renderResults(events) {
  const box = document.getElementById("results");
  box.innerHTML = "";
  for (const event of events) {
    const div = document.createElement("div");
    div.className = "result";
    div.style.setProperty("--event-color", event.color);
    const pages = event.parts.map((p) => p.pageIndex + 1).join(", ");
    div.innerHTML = `
      <div>${event.title ?? event.id}</div>
      <div class="meta">${event.method}${pages ? ` - page ${pages}` : ""}${
        event.notes.length ? ` - ${event.notes.join("; ")}` : ""
      }</div>
    `;
    div.addEventListener("click", () => {
      document.querySelectorAll(".result").forEach((c) => c.classList.remove("active"));
      div.classList.add("active");
      jumpToEvent(event);
    });
    box.appendChild(div);
  }
}

// Jump to the first highlighted part; repeated clicks cycle through parts.
const cycleState = new Map();

function jumpToEvent(event) {
  if (!instance || !event.parts.length) return;
  const index = (cycleState.get(event.id) ?? -1) + 1;
  const part = event.parts[index % event.parts.length];
  cycleState.set(event.id, index);
  const [left, top, width, height] = part.boundingBox;
  const padding = 40;
  instance.jumpToRect(
    part.pageIndex,
    new PSPDFKit.Geometry.Rect({
      left: left - padding,
      top: top - padding,
      width: width + padding * 2,
      height: height + padding * 2,
    })
  );
  emphasizePart(part, event.color);
}

// Makes the clicked highlight stand out among the others: selects the
// annotation (native selection frame) and pulses a colored outline around
// its bounding box for a couple of seconds.
let pulseTimeout = null;

async function emphasizePart(part, color) {
  if (part.annotationId) {
    try {
      await instance.setSelectedAnnotations(PSPDFKit.Immutable.List([part.annotationId]));
    } catch {
      try {
        await instance.setSelectedAnnotation(part.annotationId);
      } catch {
        // Selection is a nice-to-have; the pulse below always runs.
      }
    }
  }
  // CustomOverlayItem nodes are scaled with the zoom level by the SDK, so
  // the node is sized in raw PDF page units to match the annotation exactly.
  const [left, top, width, height] = part.boundingBox;
  const pad = 5;
  const node = document.createElement("div");
  Object.assign(node.style, {
    width: `${width + pad * 2}px`,
    height: `${height + pad * 2}px`,
    border: `3px solid ${color}`,
    borderRadius: "6px",
    boxShadow: `0 0 14px 3px ${color}`,
    boxSizing: "border-box",
    pointerEvents: "none",
  });
  node.animate(
    [{ opacity: 0 }, { opacity: 1 }, { opacity: 0.15 }, { opacity: 1 }, { opacity: 0.15 }, { opacity: 1 }, { opacity: 0 }],
    { duration: 2000, easing: "ease-in-out" }
  );
  instance.setCustomOverlayItem(
    new PSPDFKit.CustomOverlayItem({
      id: "event-pulse",
      node,
      pageIndex: part.pageIndex,
      position: new PSPDFKit.Geometry.Point({ x: left - pad, y: top - pad }),
    })
  );
  if (pulseTimeout) clearTimeout(pulseTimeout);
  pulseTimeout = setTimeout(() => {
    try {
      instance.removeCustomOverlayItem("event-pulse");
    } catch {}
  }, 2000);
}

async function processLlmOutput() {
  const btn = document.getElementById("process-btn");
  const errorBox = document.getElementById("json-error");
  errorBox.textContent = "";

  let payload;
  try {
    payload = JSON.parse(document.getElementById("llm-json").value);
  } catch (err) {
    errorBox.textContent = `Invalid JSON: ${err.message}`;
    return;
  }
  const events = Array.isArray(payload) ? payload : payload.events ?? payload.data;
  if (!Array.isArray(events) || events.length === 0) {
    errorBox.textContent = 'The JSON must be an array of events (or contain an "events" array).';
    return;
  }

  btn.disabled = true;
  btn.textContent = "Processing on server...";
  // The server deletes and re-creates every injected annotation in bulk. The
  // viewer is closed during that time and opened again afterwards: a viewer
  // that receives hundreds of deletions through Instant sync while one of
  // them is selected can fail to render.
  if (instance) {
    PSPDFKit.unload("#viewer");
    instance = null;
  }
  cycleState.clear();
  try {
    const res = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
    });
    const body = await res.json();
    if (body.error) throw new Error(body.error);
    renderResults(body.events);
    await loadViewer();
  } catch (err) {
    errorBox.textContent = `Processing failed: ${err.message}`;
    if (!instance) await loadViewer().catch(() => {});
  } finally {
    btn.disabled = false;
    btn.textContent = "Process LLM output";
  }
}

document.getElementById("process-btn").addEventListener("click", processLlmOutput);

// "Load document": upload a PDF to the server, which stores it in Document
// Engine under a fresh id and makes it the current document.
const docFileInput = document.getElementById("doc-file");
document.getElementById("load-doc-btn").addEventListener("click", () => docFileInput.click());
docFileInput.addEventListener("change", async () => {
  const file = docFileInput.files[0];
  if (!file) return;
  const btn = document.getElementById("load-doc-btn");
  const errorBox = document.getElementById("json-error");
  errorBox.textContent = "";
  btn.disabled = true;
  btn.textContent = `Uploading ${file.name}...`;
  try {
    const res = await fetch(`/api/upload-document?name=${encodeURIComponent(file.name)}`, {
      method: "POST",
      headers: { "Content-Type": "application/pdf" },
      body: file,
    });
    const body = await res.json();
    if (body.error) throw new Error(body.error);
    renderResults([]);
    cycleState.clear();
    await loadViewer();
  } catch (err) {
    errorBox.textContent = `Upload failed: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Load document (PDF)";
    docFileInput.value = "";
  }
});

async function loadPayload(id) {
  const { events } = await fetch(`/api/llm-output?payload=${encodeURIComponent(id)}`).then((r) => r.json());
  document.getElementById("llm-json").value = JSON.stringify({ events }, null, 2);
}

(async () => {
  const select = document.getElementById("payload-select");
  const payloads = await fetch("/api/payloads").then((r) => r.json());
  select.innerHTML = payloads.map((p) => `<option value="${p.id}">${p.label}</option>`).join("");
  select.addEventListener("change", () => loadPayload(select.value));
  await loadPayload(select.value);
  try {
    await loadViewer();
  } catch (err) {
    console.error("Viewer failed to load:", err);
  }
  const processed = await fetch("/api/events").then((r) => r.json());
  renderResults(processed.events);
})();
