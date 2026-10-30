"""Generates the fictitious long contract and the two sample LLM payloads.

    documents/sample-agreement-for-lease.pdf  a 40-page agreement for lease
    samples/events-scenarios.json              hand-picked events, one per
                                               positioning problem
    samples/events-pipeline.json               about 50 events in the wire
                                               format of an extraction
                                               pipeline (0-based page,
                                               character offset)

Every party, property, person, figure and date in the contract is invented.
The page numbers and character offsets of the payloads are measured on the
generated PDF, the way an extraction pipeline would measure them on its own
text layer.

    pip install -r samples/requirements.txt
    python samples/generate_contract.py
"""

import json
import random
import re
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "documents" / "sample-agreement-for-lease.pdf"

LANDLORD = "Fernhollow Properties Limited"
TENANT = "Brightquay Studios Limited"
GUARANTOR = "Garrow Holdings plc"
PROPERTY = "Units 4 and 5, Kestrel Wharf, 18 Ferry Lane, Northbridge NB1 2XY"

BODY = ParagraphStyle("body", fontName="Times-Roman", fontSize=11, leading=15, alignment=TA_JUSTIFY,
                      spaceAfter=5)
SUB = ParagraphStyle("sub", parent=BODY, leftIndent=12 * mm, firstLineIndent=-12 * mm)
SUBSUB = ParagraphStyle("subsub", parent=BODY, leftIndent=22 * mm, firstLineIndent=-10 * mm)
HEAD = ParagraphStyle("head", parent=BODY, fontName="Times-Bold", fontSize=11.5, spaceBefore=8, spaceAfter=6,
                      alignment=0)
TITLE = ParagraphStyle("title", parent=BODY, fontName="Times-Bold", fontSize=20, leading=26, alignment=TA_CENTER)
CENTER = ParagraphStyle("center", parent=BODY, alignment=TA_CENTER)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=9, leading=11.5, alignment=0, spaceAfter=0)


def q(term):
    return f"“{term}”"  # curly quotes, as a word processor types them


# ------------------------------------------------------------ the text

DEFINITIONS = [
    ("Access Date", "the date eight weeks before the Target Handover Date, or such other date as the Landlord "
                    "and the Tenant agree in writing"),
    ("Agreed Form", "in the form of the draft annexed to this Agreement and initialled by or on behalf of the "
                    "parties, with such amendments as the parties agree in writing"),
    ("Building", "the building known as Kestrel Wharf, 18 Ferry Lane, Northbridge NB1 2XY"),
    ("Building Contract", "the contract to be entered into between the Landlord and the Contractor for the "
                          "carrying out of the Landlord's Works"),
    ("Certificate of Practical Completion", "the certificate issued by the Landlord's Surveyor under clause 6.3"),
    ("Contractor", "the building contractor appointed by the Landlord to carry out the Landlord's Works"),
    ("Defects Liability Period", "the period of twelve months starting on the Handover Date"),
    ("Handover Date", "the date on which the Certificate of Practical Completion is issued or, if later, the "
                      "date on which the Landlord gives vacant possession of the Property to the Tenant"),
    ("Initial Rent", "four hundred and eighty-six thousand five hundred pounds (£486,500) a year, exclusive "
                     "of VAT"),
    ("Landlord's Surveyor", "Ashdown Pike LLP or such other chartered surveyor as the Landlord may appoint "
                            "from time to time"),
    ("Landlord's Works", "the works to the Property described in Schedule 1"),
    ("Lease", "the lease of the Property to be granted under this Agreement in the Agreed Form"),
    ("Lease Date", "the date on which the Lease is completed under clause 9"),
    ("Longstop Date", "31 March 2028"),
    ("Planning Condition", "the condition set out in clause 2.2"),
    ("Planning Longstop Date", "31 December 2026"),
    ("Practical Completion", "practical completion of the Landlord's Works as certified under clause 6"),
    ("Property", f"{PROPERTY}, shown edged red on the plan annexed to this Agreement"),
    ("Rent Commencement Date", "the date nine months after the Lease Date"),
    ("Rent Deposit", "the sum of two hundred and forty-three thousand two hundred and fifty pounds (£243,250)"),
    ("Snagging Items", "minor defects and omissions which do not prevent the Property from being used for its "
                       "intended purpose"),
    ("Target Handover Date", "30 June 2027"),
    ("Tenant's Surveyor", "Linwood Carver Associates or such other chartered surveyor as the Tenant may appoint "
                          "from time to time"),
    ("Tenant's Works", "the works of fitting out the Property for the Permitted Use, described in Schedule 2"),
    ("Term", "fifteen years from and including the Lease Date"),
    ("Working Day", "any day which is not a Saturday, a Sunday or a bank holiday in England"),
]

# Each clause: (title, [subclauses]). A subclause is a string or (text, [items]).
CLAUSES = [
    ("CONDITIONS", [
        "This Agreement, other than this clause 2 and clauses 13 to 27, is conditional on the satisfaction of "
        "the Planning Condition on or before the Planning Longstop Date.",
        "The Planning Condition is the grant of a planning permission for the change of use of the Property to "
        "use as offices and production studios, on terms reasonably satisfactory to the Tenant.",
        "The Landlord shall use all reasonable endeavours to satisfy the Planning Condition as soon as reasonably "
        "practicable and shall keep the Tenant informed of the progress of the application.",
        "If the Planning Condition has not been satisfied by the Planning Longstop Date, either party may "
        "terminate this Agreement by giving written notice to the other at any time before the Planning "
        "Condition is satisfied.",
        "The Landlord shall give the Tenant written notice within five Working Days after the Planning Condition "
        "is satisfied.",
    ]),
    ("THE LANDLORD'S WORKS", [
        "The Landlord shall carry out the Landlord's Works, or procure that they are carried out, in a good and "
        "workmanlike manner, with good quality materials, and in accordance with all statutory requirements, "
        "the planning permission and the requirements of the insurers of the Building.",
        "The Landlord shall use all reasonable endeavours to procure that the Landlord's Works start within six "
        "weeks after the date on which the Planning Condition is satisfied.",
        "The Landlord shall use all reasonable endeavours to procure that Practical Completion takes place on "
        "or before the Target Handover Date.",
        "The Landlord shall not use any deleterious materials in the Landlord's Works, and shall procure that "
        "the Contractor and every consultant gives a warranty to that effect.",
        "The Landlord shall keep the Tenant informed of the progress of the Landlord's Works and shall send to "
        "the Tenant a copy of each monthly progress report prepared by the Contractor within five Working Days "
        "after receiving it.",
        "The Tenant and the Tenant's Surveyor may inspect the Landlord's Works at reasonable times on giving "
        "reasonable prior notice, provided that they comply with the reasonable requirements of the Contractor "
        "and do not give any instruction to the Contractor.",
    ]),
    ("VARIATIONS", [
        "The Landlord may make variations to the Landlord's Works which are required to comply with statutory "
        "requirements, or which are minor and do not materially affect the Tenant's use of the Property, "
        "without the consent of the Tenant.",
        "Any other variation requires the prior written consent of the Tenant, which shall not be unreasonably "
        "withheld or delayed.",
        "The Tenant may request variations to the Landlord's Works. The Landlord shall respond within ten "
        "Working Days with an estimate of the cost of the variation and of its effect on the Target Handover "
        "Date.",
        "The Tenant shall pay the reasonable and proper cost of any variation it requests within twenty "
        "Working Days after written demand, together with VAT.",
    ]),
    ("ACCESS BEFORE THE HANDOVER DATE", [
        "From the Access Date the Tenant may enter the Property to carry out the design and preparation of the "
        "Tenant's Works and the installation of its data cabling, subject to the reasonable requirements of the "
        "Contractor.",
        "The Tenant's access under clause 5.1 is at the Tenant's own risk, and the Tenant shall indemnify the "
        "Landlord against any loss arising from that access.",
        "Access under clause 5.1 shall not constitute occupation of the Property and shall not create any "
        "tenancy.",
        "The Tenant shall comply with the health and safety rules of the Contractor while it is on the Property.",
    ]),
    ("PRACTICAL COMPLETION", [
        "The Landlord shall give the Tenant at least ten Working Days' notice of the date on which the "
        "Landlord's Surveyor intends to inspect the Landlord's Works with a view to certifying Practical "
        "Completion.",
        "The Tenant and the Tenant's Surveyor may attend the inspection and make representations to the "
        "Landlord's Surveyor, who shall have proper regard to them.",
        "The Landlord's Surveyor shall issue the Certificate of Practical Completion when, in the reasonable "
        "opinion of the Landlord's Surveyor, the Landlord's Works have been completed except for Snagging Items.",
        "The Landlord shall send a copy of the Certificate of Practical Completion to the Tenant on the day it "
        "is issued, together with a list of the Snagging Items.",
        "The Landlord shall remedy the Snagging Items within twenty Working Days after the Handover Date, at "
        "times agreed with the Tenant so as to cause as little disruption as possible.",
        "If the Tenant disputes the issue of the Certificate of Practical Completion, the dispute shall be "
        "referred to an expert under clause 17, but the Certificate shall remain valid unless and until the "
        "expert decides otherwise.",
    ]),
    ("HANDOVER DATE AND DELAY", [
        "The Landlord shall give vacant possession of the Property to the Tenant on the Handover Date.",
        "If the Handover Date has not occurred by the Target Handover Date, the rent-free period under the "
        "Lease shall be extended by one day for each day of delay after the Target Handover Date until the "
        "Handover Date.",
        "The extension of the rent-free period under clause 7.2 is the sole remedy of the Tenant for any delay "
        "in the Handover Date, except where the delay is caused by the wilful default of the Landlord.",
        "If the Handover Date has not occurred by the Longstop Date, the Tenant may terminate this Agreement by "
        "giving written notice to the Landlord at any time before the Handover Date.",
        "The Longstop Date shall be extended by one day for each day of delay caused by any event of force "
        "majeure, up to a maximum of ninety days.",
    ]),
    ("THE TENANT'S WORKS", [
        "The Tenant shall carry out the Tenant's Works in accordance with the plans and specifications approved "
        "by the Landlord, which approval shall not be unreasonably withheld or delayed.",
        "The Tenant shall start the Tenant's Works within eight weeks after the Handover Date and shall use all "
        "reasonable endeavours to complete them within twenty-six weeks after the Handover Date.",
        "The Tenant shall not carry out any works which affect the structure of the Building or its mechanical "
        "and electrical systems without the prior written consent of the Landlord.",
        "On completion of the Tenant's Works, the Tenant shall give the Landlord a copy of the as-built drawings "
        "and of the health and safety file.",
    ]),
    ("GRANT OF THE LEASE", [
        "The Landlord shall grant and the Tenant shall accept the Lease on the Handover Date, or within five "
        "Working Days after it.",
        "The Lease shall be granted for the Term at the Initial Rent, payable from the Rent Commencement Date, "
        "with rent reviews on the fifth and tenth anniversaries of the Lease Date.",
        "The Tenant may terminate the Lease on the tenth anniversary of the Lease Date by giving the Landlord "
        "not less than twelve months' written notice, subject to the conditions set out in the Lease.",
        "The Guarantor shall execute the Lease as guarantor of the obligations of the Tenant.",
        "The Tenant shall pay the Rent Deposit to the Landlord on the Lease Date, to be held on the terms of a "
        "rent deposit deed in the Agreed Form.",
        "The Tenant shall pay the stamp duty land tax and registration fees payable on the Lease.",
    ]),
    ("DEFECTS", [
        "The Landlord shall remedy, at its own cost, any defects in the Landlord's Works which appear during "
        "the Defects Liability Period and which are notified by the Tenant in writing within that period.",
        "The Landlord shall remedy each notified defect as soon as reasonably practicable, and in the case of an "
        "urgent defect affecting the security or the weathertightness of the Property within forty-eight hours.",
        "The Tenant shall give the Landlord and the Contractor reasonable access to the Property to remedy "
        "defects.",
        "The Landlord shall enforce the obligations of the Contractor under the Building Contract in relation to "
        "defects for the benefit of the Tenant.",
    ]),
    ("COLLATERAL WARRANTIES", [
        "The Landlord shall procure that the Contractor and each consultant with a design responsibility gives "
        "a collateral warranty to the Tenant in the Agreed Form within twenty Working Days after the Handover "
        "Date.",
        "Each collateral warranty shall be capable of assignment twice without consent.",
        "The Landlord shall procure that each consultant maintains professional indemnity insurance of not less "
        "than five million pounds (£5,000,000) for twelve years after Practical Completion.",
    ]),
    ("INSURANCE", [
        "The Landlord shall insure the Landlord's Works and all materials on the Property against the insured "
        "risks until the Handover Date.",
        "If the Landlord's Works are damaged by an insured risk before the Handover Date, the Landlord shall "
        "reinstate them with all reasonable speed, and the Target Handover Date and the Longstop Date shall be "
        "extended accordingly.",
        "From the Handover Date, the Property shall be insured in accordance with the Lease.",
    ]),
    ("TERMINATION", [
        "Either party may terminate this Agreement by notice to the other if the other party is in material "
        "breach of its obligations and has not remedied the breach within twenty Working Days after receiving "
        "written notice of it.",
        "Either party may terminate this Agreement by notice to the other if the other party becomes insolvent.",
        "Termination of this Agreement shall be without prejudice to any right or remedy of either party in "
        "respect of any earlier breach.",
        "On termination of this Agreement, the Tenant shall remove its property from the Property within ten "
        "Working Days and shall make good any damage caused by its removal.",
    ]),
    ("NOTICES", [
        "Any notice given under this Agreement shall be in writing and delivered by hand or sent by recorded "
        "delivery to the address of the recipient given in this Agreement, or to such other address as the "
        "recipient may notify.",
        "A notice delivered by hand is given when it is left at the address. A notice sent by recorded delivery "
        "is given on the second Working Day after posting.",
        "A notice given under this Agreement is not valid if sent by email.",
    ]),
    ("ASSIGNMENT", [
        "This Agreement is personal to the Tenant, and the Tenant shall not assign, charge or otherwise deal "
        "with the benefit of this Agreement.",
        "The Landlord may assign the benefit of this Agreement to a purchaser of its interest in the Building, "
        "provided that the purchaser enters into a deed of covenant with the Tenant to observe the obligations "
        "of the Landlord.",
    ]),
    ("VAT", [
        "All sums payable under this Agreement are exclusive of VAT, which shall be paid in addition at the rate "
        "applicable at the time.",
        "The Landlord confirms that it has opted to tax the Building for VAT purposes.",
    ]),
    ("DISPUTES", [
        "Any dispute about the Landlord's Works, Practical Completion, defects or the extension of the Target "
        "Handover Date shall be referred to an independent expert.",
        "The expert shall be a chartered building surveyor with at least ten years' experience of commercial "
        "property, agreed by the parties or, failing agreement, nominated by the President of the Royal "
        "Institution of Chartered Surveyors.",
        "The expert shall act as an expert and not as an arbitrator. The decision of the expert is final and "
        "binding on the parties, except in the case of manifest error.",
        "The costs of the expert shall be borne as the expert directs.",
    ]),
    ("DATA PROTECTION", [
        "Each party shall comply with data protection legislation in relation to any personal data it processes "
        "in connection with this Agreement.",
        "Neither party shall transfer personal data received from the other outside the United Kingdom without "
        "the prior written consent of the other.",
    ]),
    ("CONFIDENTIALITY", [
        "Each party shall keep the terms of this Agreement confidential and shall not disclose them to any "
        "person, except to its professional advisers, its lenders and prospective purchasers of its interest, "
        "or as required by law, by any regulatory authority or by the rules of any stock exchange on which its "
        "shares are listed, and in each case only to the extent necessary, and each party shall procure that "
        "any person to whom it discloses those terms keeps them confidential on the same basis as if that "
        "person were a party to this Agreement.",
        "The obligations in this clause 19 shall continue to apply for a period of two years after the Lease "
        "Date or the earlier termination of this Agreement.",
    ]),
    ("ANTI-BRIBERY", [
        "Each party shall comply with all applicable laws relating to anti-bribery and anti-corruption, and shall "
        "not do anything which would cause the other party to breach those laws.",
    ]),
    ("NON-MERGER", [
        "The provisions of this Agreement shall remain in force after the grant of the Lease in so far as any "
        "of them remain to be performed.",
    ]),
    ("ENTIRE AGREEMENT", [
        "This Agreement and the documents annexed to it constitute the whole agreement between the parties and "
        "supersede all previous agreements between them relating to its subject matter.",
        "Each party acknowledges that in entering into this Agreement it has not relied on any representation "
        "or warranty, except those set out in this Agreement or given in written replies to enquiries by the "
        "solicitors of one party to the solicitors of the other before the date of this Agreement.",
    ]),
    ("JOINT AND SEVERAL LIABILITY", [
        "Where a party comprises more than one person, the obligations of those persons are joint and several.",
    ]),
    ("THIRD PARTY RIGHTS", [
        "A person who is not a party to this Agreement shall not have any rights under the Contracts (Rights of "
        "Third Parties) Act 1999 to enforce any term of this Agreement.",
    ]),
    ("GUARANTEE", [
        "In consideration of the Landlord entering into this Agreement at its request, the Guarantor guarantees "
        "to the Landlord that the Tenant shall perform its obligations under this Agreement.",
        "The liability of the Guarantor shall not be affected by any time or indulgence granted to the Tenant, "
        "or by any variation of this Agreement.",
    ]),
    ("COUNTERPARTS", [
        "This Agreement may be executed in any number of counterparts, each of which when executed shall "
        "constitute a duplicate original, but all the counterparts together shall constitute one agreement.",
    ]),
    ("GOVERNING LAW AND JURISDICTION", [
        "This Agreement and any dispute or claim arising out of or in connection with it shall be governed by "
        "the law of England and Wales.",
        "The courts of England and Wales shall have exclusive jurisdiction to settle any dispute or claim "
        "arising out of or in connection with this Agreement, subject to clause 17.",
    ]),
]

FLOORS = ["Ground floor", "First floor", "Second floor", "Third floor", "Roof"]
ELEMENTS = [
    ("External walls", "Repair and repoint brickwork; replace defective lintels; apply breathable masonry "
                       "protection to all elevations."),
    ("Windows", "Replace windows with thermally broken aluminium double glazed units, U-value not exceeding "
                "1.4 W/m²K, with trickle vents."),
    ("Floors", "Level the structural slab to SR2 tolerance; install a raised access floor with a finished "
               "floor zone of 150 mm."),
    ("Ceilings", "Expose and clean the soffit; install acoustic rafts to 40 per cent of the floor area."),
    ("Mechanical", "Install a variable refrigerant flow system with fresh air heat recovery, designed for one "
                   "person per 8 m² of net internal area."),
    ("Electrical", "Install the main distribution, sub-metered per floor, with small power capacity of 25 "
                   "W/m²."),
    ("Lighting", "Install LED panels with daylight dimming, average maintained illuminance of 400 lux at desk "
                 "height."),
    ("Fire safety", "Install an L1 fire alarm system and an automatic sprinkler system to the relevant "
                    "standard."),
    ("Sanitary", "Provide WC cores to the ratio of one WC per 10 persons, including one accessible WC."),
    ("Finishes", "Paint walls in an agreed white; install entrance matting and floor finishes to the "
                 "common parts."),
]


# --------------------------------------------------------------- build

def build_story():
    s = []
    s += [Spacer(1, 50 * mm), Paragraph("DATED&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2026", CENTER),
          Spacer(1, 20 * mm), Paragraph(f"(1) {LANDLORD.upper()}", CENTER),
          Paragraph(f"(2) {TENANT.upper()}", CENTER), Paragraph(f"(3) {GUARANTOR.upper()}", CENTER),
          Spacer(1, 25 * mm), Paragraph("AGREEMENT FOR LEASE", TITLE), Spacer(1, 6 * mm),
          Paragraph(f"relating to {PROPERTY}", CENTER), Spacer(1, 60 * mm),
          Paragraph("This document is a fictitious sample generated for a software demonstration. It is not "
                    "legal advice and must not be used as a precedent.", CENTER),
          PageBreak()]

    s.append(Paragraph("CONTENTS", HEAD))
    titles = ["DEFINITIONS AND INTERPRETATION"] + [c[0] for c in CLAUSES]
    for i, t in enumerate(titles, start=1):
        s.append(Paragraph(f"{i}.&nbsp;&nbsp;{t.title()}", BODY))
    for i, t in enumerate(["The Landlord's Works", "The Tenant's Works", "Principal terms of the Lease",
                           "Rent and rent-free periods", "Programme", "Schedule of condition",
                           "Form of collateral warranty"], start=1):
        s.append(Paragraph(f"Schedule {i}&nbsp;&nbsp;{t}", BODY))
    s.append(PageBreak())

    s.append(Paragraph(f"THIS AGREEMENT is dated&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2026", BODY))
    s.append(Paragraph("PARTIES", HEAD))
    s.append(Paragraph(f"(1)&nbsp;&nbsp;{LANDLORD.upper()}, incorporated and registered in England and Wales with "
                       "company number 00000001, whose registered office is at 2 Mill Yard, Northbridge NB1 4AA "
                       f"(the {q('Landlord')}).", SUB))
    s.append(Paragraph(f"(2)&nbsp;&nbsp;{TENANT.upper()}, incorporated and registered in England and Wales with "
                       "company number 00000002, whose registered office is at 9 Lantern Row, Eastwick EW2 3BB "
                       f"(the {q('Tenant')}).", SUB))
    s.append(Paragraph(f"(3)&nbsp;&nbsp;{GUARANTOR.upper()}, incorporated and registered in England and Wales with "
                       "company number 00000003, whose registered office is at 9 Lantern Row, Eastwick EW2 3BB "
                       f"(the {q('Guarantor')}).", SUB))
    s.append(Paragraph("BACKGROUND", HEAD))
    s.append(Paragraph("(A)&nbsp;&nbsp;The Landlord is the owner of the freehold interest in the Building.", SUB))
    s.append(Paragraph("(B)&nbsp;&nbsp;The Landlord has agreed to carry out the Landlord's Works and to grant, and "
                       "the Tenant has agreed to accept, the Lease on the terms of this Agreement.", SUB))
    s.append(Paragraph("AGREED TERMS", HEAD))

    s.append(Paragraph("1.&nbsp;&nbsp;DEFINITIONS AND INTERPRETATION", HEAD))
    s.append(Paragraph("1.1&nbsp;&nbsp;&nbsp;The definitions in this clause apply in this Agreement.", SUB))
    for term, meaning in DEFINITIONS:
        s.append(Paragraph(f"{q(term)}: {meaning}.", SUBSUB))
    for n, text in enumerate([
        "Clause, Schedule and paragraph headings shall not affect the interpretation of this Agreement.",
        "A reference to a clause or a Schedule is to a clause of, or a Schedule to, this Agreement.",
        "Unless the context otherwise requires, words in the singular include the plural and words in the "
        "plural include the singular.",
        "A reference to a statute or a statutory provision is a reference to it as amended, extended or "
        "re-enacted from time to time.",
        "A reference to writing or written does not include email, except where expressly stated.",
        "Any obligation on a party not to do something includes an obligation not to allow that thing to be "
        "done.",
    ], start=2):
        s.append(Paragraph(f"1.{n}&nbsp;&nbsp;&nbsp;{text}", SUB))

    for number, (title, subs) in enumerate(CLAUSES, start=2):
        s.append(Paragraph(f"{number}.&nbsp;&nbsp;{title}", HEAD))
        for i, text in enumerate(subs, start=1):
            s.append(Paragraph(f"{number}.{i}&nbsp;&nbsp;&nbsp;{text}", SUB))

    s.append(Paragraph("This Agreement has been entered into on the date stated at the beginning of it.", BODY))

    # Schedules
    s += [PageBreak(), Paragraph("SCHEDULE 1&nbsp;&nbsp;THE LANDLORD'S WORKS", HEAD),
          Paragraph("The Landlord's Works comprise the following works to each floor of the Property, carried out "
                    "in accordance with the specification below and the drawings listed in the Building "
                    "Contract.", BODY)]
    rows = [["Ref", "Floor", "Element", "Specification"]]
    ref = 1
    for floor in FLOORS:
        for element, spec in ELEMENTS:
            if floor == "Roof" and element in ("Floors", "Sanitary", "Lighting", "Ceilings"):
                continue
            rows.append([f"LW{ref:03}", floor, element, spec])
            ref += 1
    s.append(table(rows, [16 * mm, 26 * mm, 28 * mm, 100 * mm]))

    s += [PageBreak(), Paragraph("SCHEDULE 2&nbsp;&nbsp;THE TENANT'S WORKS", HEAD)]
    for i, text in enumerate([
        "Installation of partitions, meeting rooms and production studios in accordance with the approved plans.",
        "Acoustic treatment of the studios to achieve a sound reduction of not less than 55 dB between the "
        "studios and the adjoining offices.",
        "Installation of a kitchen and breakout area on the first floor.",
        "Installation of data cabling, a communications room and supplementary cooling to the communications "
        "room.",
        "Installation of furniture, signage within the Property and audio-visual equipment.",
        "Any works required to the mechanical and electrical systems to serve the Tenant's layout, subject to "
        "clause 8.3.",
    ], start=1):
        s.append(Paragraph(f"{i}.&nbsp;&nbsp;&nbsp;{text}", SUB))

    s += [PageBreak(), Paragraph("SCHEDULE 3&nbsp;&nbsp;PRINCIPAL TERMS OF THE LEASE", HEAD)]
    s.append(table([["Term of the Lease", "Provision"],
                    ["Term", "Fifteen years from and including the Lease Date"],
                    ["Initial Rent", "£486,500 a year exclusive of VAT, payable quarterly in advance"],
                    ["Rent-free period", "Nine months from the Lease Date, extended under clause 7.2 for delay"],
                    ["Rent reviews", "Upwards only, to open market rent, on the fifth and tenth anniversaries of "
                                     "the Lease Date"],
                    ["Tenant's break option", "Tenth anniversary of the Lease Date, on twelve months' written "
                                              "notice"],
                    ["Repair", "Full repairing, limited by reference to a schedule of condition"],
                    ["Alienation", "Assignment of the whole with consent; underletting of the whole or of a "
                                   "floor with consent"],
                    ["Permitted Use", "Offices and production studios"],
                    ["Service charge", "Fair proportion of the costs of the services to the Building"],
                    ["Rent Deposit", "£243,250, to be released on the third anniversary of the Lease Date "
                                     "if the Tenant meets the release conditions"]],
                   [50 * mm, 120 * mm]))

    s += [PageBreak(), Paragraph("SCHEDULE 4&nbsp;&nbsp;RENT AND RENT-FREE PERIODS", HEAD),
          Paragraph("The table below shows the rent payable in each year of the Term, assuming that the Lease "
                    "Date is 1 July 2027 and that no rent review increases the rent. It is for information only "
                    "and does not form part of the terms of the Lease.", BODY)]
    rows = [["Lease year", "From", "To", "Rent payable (£)", "Note"]]
    for year in range(1, 16):
        start, end = f"1 July {2026 + year}", f"30 June {2027 + year}"
        rent = "121,625" if year == 1 else "486,500"
        note = "Nine months rent free" if year == 1 else ("Rent review" if year in (6, 11) else
                                                           ("Break date at end of year" if year == 10 else ""))
        rows.append([str(year), start, end, rent, note])
    s.append(table(rows, [20 * mm, 32 * mm, 32 * mm, 36 * mm, 50 * mm]))

    s += [PageBreak(), Paragraph("SCHEDULE 5&nbsp;&nbsp;PROGRAMME", HEAD),
          Paragraph("The programme below is the Landlord's current estimate. It does not form part of the "
                    "obligations of the Landlord, which are set out in clauses 3 and 7.", BODY)]
    rows = [["Activity", "Start", "Finish", "Duration"]]
    for activity, start, finish, weeks in [
        ("Planning application determined", "1 September 2026", "30 November 2026", "13 weeks"),
        ("Building Contract entered into", "1 December 2026", "15 December 2026", "2 weeks"),
        ("Strip out and enabling works", "4 January 2027", "12 February 2027", "6 weeks"),
        ("External envelope and windows", "15 February 2027", "7 May 2027", "12 weeks"),
        ("Mechanical and electrical first fix", "1 March 2027", "30 April 2027", "9 weeks"),
        ("Raised floors and ceilings", "3 May 2027", "28 May 2027", "4 weeks"),
        ("Tenant access for data cabling", "5 May 2027", "30 June 2027", "8 weeks"),
        ("Mechanical and electrical second fix", "3 May 2027", "11 June 2027", "6 weeks"),
        ("Commissioning and testing", "14 June 2027", "25 June 2027", "2 weeks"),
        ("Practical Completion inspection", "28 June 2027", "29 June 2027", "2 days"),
        ("Target Handover Date", "30 June 2027", "30 June 2027", "-"),
    ]:
        rows.append([activity, start, finish, weeks])
    s.append(table(rows, [70 * mm, 36 * mm, 36 * mm, 28 * mm]))

    s += [PageBreak(), Paragraph("SCHEDULE 6&nbsp;&nbsp;SCHEDULE OF CONDITION", HEAD),
          Paragraph("The condition of the Property at the date of this Agreement, recorded by the Landlord's "
                    "Surveyor and agreed by the Tenant's Surveyor. The photographs referred to are held by both "
                    "surveyors. The Tenant shall not be required to put the Property into any better state of "
                    "repair than that recorded in this Schedule, as improved by the Landlord's Works.", BODY)]
    s.append(table(condition_rows(), [16 * mm, 30 * mm, 34 * mm, 20 * mm, 70 * mm]))

    s += [PageBreak(), Paragraph("SCHEDULE 7&nbsp;&nbsp;FORM OF COLLATERAL WARRANTY", HEAD),
          Paragraph(f"THIS DEED is made between (1) the Contractor or consultant giving the warranty (the "
                    f"{q('Warrantor')}), (2) {TENANT.upper()} (the {q('Beneficiary')}) and (3) {LANDLORD.upper()} "
                    f"(the {q('Employer')}).", BODY)]
    for i, text in enumerate(WARRANTY, start=1):
        s.append(Paragraph(f"{i}.&nbsp;&nbsp;&nbsp;{text}", SUB))

    s += [PageBreak(), Paragraph("EXECUTION", HEAD)]
    for party in (LANDLORD, TENANT, GUARANTOR):
        s.append(KeepTogether([
            Paragraph(f"Executed as a deed by {party.upper()} acting by a director, in the presence of a witness:",
                      BODY),
            Spacer(1, 10 * mm), Paragraph("Director ......................................", BODY),
            Paragraph("Witness signature ......................................", BODY),
            Paragraph("Witness name ......................................", BODY),
            Paragraph("Witness address ......................................", BODY), Spacer(1, 8 * mm)]))
    return s


WARRANTY = [
    "The Warrantor warrants to the Beneficiary that it has performed and will continue to perform its "
    "obligations under its appointment or building contract with the Employer, and that it has exercised and will "
    "continue to exercise all the reasonable skill, care and diligence to be expected of a properly qualified and "
    "competent member of its profession or trade experienced in carrying out works or services of a similar size, "
    "scope and complexity.",
    "The Warrantor warrants that it has not specified or used, and will not specify or use, any materials which "
    "are generally accepted in the construction industry at the time of specification or use as deleterious to "
    "health and safety or to the durability of buildings in the particular circumstances in which they are used.",
    "The Warrantor shall have no greater liability to the Beneficiary under this deed than it would have had if "
    "the Beneficiary had been named as a joint employer with the Employer under the appointment or building "
    "contract.",
    "The Warrantor may rely on any limit of liability or other term of the appointment or building contract, "
    "and may raise the equivalent rights of defence as it would have had if the Beneficiary had been named as a "
    "joint employer.",
    "The Warrantor shall maintain professional indemnity insurance with a limit of indemnity of not less than "
    "five million pounds (\u00a35,000,000) for each and every claim for a period of twelve years from the date "
    "of practical completion of the works, provided that such insurance remains available at commercially "
    "reasonable rates.",
    "The Beneficiary shall have an irrevocable, royalty-free, non-exclusive licence to copy and use the "
    "drawings, specifications and other documents prepared by or on behalf of the Warrantor for any purpose "
    "related to the Property, including its use, maintenance, repair, letting and reinstatement.",
    "The Beneficiary may assign the benefit of this deed without the consent of the Warrantor on two occasions "
    "only, by way of absolute legal assignment, to a person who takes an assignment of the Beneficiary's "
    "interest in the Property.",
    "No action or proceedings for any breach of this deed shall be commenced against the Warrantor after the "
    "expiry of twelve years from the date of practical completion of the works.",
    "Any notice to be given under this deed shall be in writing and delivered by hand or sent by recorded "
    "delivery to the registered office of the recipient.",
    "This deed and any dispute or claim arising out of or in connection with it shall be governed by the law of "
    "England and Wales, and the courts of England and Wales shall have exclusive jurisdiction.",
]

AREAS = ["Reception", "Open plan office (north)", "Open plan office (south)", "Open plan office (east)",
         "Meeting room 1", "Meeting room 2", "Meeting room 3", "Kitchen", "WC core A", "WC core B", "Shower room",
         "Stair core 1", "Stair core 2", "Lift lobby", "Riser 1", "Riser 2"]
CONDITION = {
    "Floor": ["Carpet tiles worn at the entrance, staining near the doors", "Vinyl lifting at two joints",
              "Raised floor panels rocking in three places", "Screed exposed, minor cracking", "Fair condition"],
    "Walls": ["Paint scuffed at low level", "Minor hairline cracks above the door head", "Plaster damaged around "
              "redundant sockets", "Damp staining below the window cill", "Fair condition"],
    "Ceiling": ["Ceiling tiles stained near the riser", "Missing tiles in the grid", "Grid bent at the light "
                "fittings", "Exposed soffit, old fixings left in place", "Fair condition"],
    "Windows": ["Sealed units misted in two panes", "Ironmongery missing on one opening light", "Seals perished "
                "on the north elevation", "Cill boards chipped", "Fair condition"],
    "Doors": ["Door closer leaking oil", "Vision panel cracked", "Frame damaged at the latch side",
              "Door binding on the floor finish", "Fair condition"],
}


def condition_rows():
    rng = random.Random(4)
    rows = [["Ref", "Floor", "Area", "Element", "Condition"]]
    ref = 1
    for floor in ["Lower ground floor"] + FLOORS[:4]:
        for area in AREAS:
            for element, notes in CONDITION.items():
                note = rng.choice(notes)
                if note != "Fair condition":
                    note += f" (photo {ref:03})"
                rows.append([f"SC{ref:03}", floor, area, element, note])
                ref += 1
    return rows


def table(rows, widths):
    data = [[Paragraph(str(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6"))]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    if doc.page > 1:
        canvas.drawCentredString(A4[0] / 2, 12 * mm, str(doc.page))
    canvas.restoreState()


# ------------------------------------------------------------ payloads

def page_texts():
    """Page text in reading order, lines joined by newlines, as a text layer
    gives it to a pipeline."""
    reader = PdfReader(str(PDF))
    return [page.extract_text() or "" for page in reader.pages]


def flex(text):
    """Regex for a phrase that tolerates line breaks and either kind of quote."""
    out = re.escape(text)
    out = re.sub(r"(\\ )+", r"\\s+", out)
    return out.replace("“", "[\"“]").replace("”", "[\"”]").replace("'", "['’]")


def occurrences(pages, phrase):
    """[(page_index, start, end)] of every occurrence of the phrase."""
    found = []
    for i, text in enumerate(pages):
        for m in re.finditer(flex(phrase), text):
            found.append((i, m.start(), m.end()))
    return found


def pipeline_events(pages):
    """Events in the wire format of an extraction pipeline: the trigger string
    as the LLM returned it, a 0-based page number and the character offset of
    the trigger in the page text. nAppereance counts the events emitted per
    trigger string, not the position of the occurrence in the document."""
    spec = [
        # (title, description, date, trigger, where): where is the index of the occurrence in the
        # document (0 = first, -1 = last), or a longer phrase around the trigger that occurs once.
        ("Agreement date", "The agreement is dated in 2026; the day and month are left blank.", "2026-01-01",
         "THIS AGREEMENT is dated", 0),
        ("Planning Longstop Date", "Date by which the Planning Condition must be satisfied.", "2026-12-31",
         "31 December 2026", 0),
        ("Termination for planning failure", "Either party may terminate if the Planning Condition is not "
         "satisfied by the Planning Longstop Date.", "2026-12-31",
         "If the Planning Condition has not been satisfied by the Planning Longstop Date", 0),
        ("Notice of planning satisfaction", "Landlord notifies the Tenant within five Working Days after the "
         "Planning Condition is satisfied.", None, "within five Working Days after the Planning Condition", 0),
        ("Start of the Landlord's Works", "Works to start within six weeks after the Planning Condition is "
         "satisfied.", None, "start within six weeks after the date on which the Planning Condition is satisfied",
         0),
        ("Target Handover Date (definition)", "Defined term.", "2027-06-30", "30 June 2027", 0),
        ("Target Handover Date (Practical Completion)", "Landlord to use reasonable endeavours to achieve "
         "Practical Completion by the Target Handover Date.", "2027-06-30", "Target Handover Date",
         "Practical Completion takes place on or before the Target Handover Date"),
        ("Target Handover Date (delay)", "Rent-free period extended day for day after the Target Handover Date.",
         "2027-06-30", "Target Handover Date", "each day of delay after the Target Handover Date"),
        ("Longstop Date (definition)", "Defined term.", "2028-03-31", "31 March 2028", 0),
        ("Tenant termination at Longstop Date", "Tenant may terminate if the Handover Date has not occurred by "
         "the Longstop Date.", "2028-03-31", "If the Handover Date has not occurred by the Longstop Date", 0),
        ("Longstop Date extension", "Force majeure extends the Longstop Date by up to ninety days.", None,
         "up to a maximum of ninety days", 0),
        ("Access Date", "Tenant access for fit-out preparation eight weeks before the Target Handover Date.",
         "2027-05-05", "the date eight weeks before the Target Handover Date", 0),
        ("Practical Completion inspection notice", "Ten Working Days' notice of the inspection.", None,
         "at least ten Working Days' notice", 0),
        ("Snagging period", "Snagging Items remedied within twenty Working Days after the Handover Date.", None,
         "within twenty Working Days after the Handover Date", 0),
        ("Handover Date", "Vacant possession given on the Handover Date.", None,
         "vacant possession of the Property to the Tenant on the Handover Date", 0),
        ("Start of the Tenant's Works", "Within eight weeks after the Handover Date.", None,
         "within eight weeks after the Handover Date", 0),
        ("Completion of the Tenant's Works", "Within twenty-six weeks after the Handover Date.", None,
         "within twenty-six weeks after the Handover Date", 0),
        ("Lease Date", "Lease granted on the Handover Date or within five Working Days after it.", None,
         "within five Working Days after it", 0),
        ("Rent Commencement Date", "Nine months after the Lease Date.", None,
         "the date nine months after the Lease Date", 0),
        ("Term", "Fifteen years from and including the Lease Date.", None,
         "fifteen years from and including the Lease Date", 0),
        ("Rent review dates", "Fifth and tenth anniversaries of the Lease Date.", None,
         "the fifth and tenth anniversaries of the Lease Date", 0),
        ("Break date", "Tenant break on the tenth anniversary on twelve months' notice.", None,
         "on the tenth anniversary of the Lease Date", 0),
        ("Break notice", "Not less than twelve months' written notice.", None,
         "not less than twelve months' written notice", 0),
        ("Rent Deposit paid", "Rent Deposit paid on the Lease Date.", None,
         "shall pay the Rent Deposit to the Landlord on the Lease Date", 0),
        ("Defects Liability Period (definition)", "Twelve months from the Handover Date.", None,
         "the period of twelve months starting on the Handover Date", 0),
        ("Urgent defects", "Urgent defects remedied within forty-eight hours.", None,
         "within forty-eight hours", 0),
        ("Collateral warranties", "Warranties within twenty Working Days after the Handover Date.", None,
         "within twenty Working Days after the Handover", 1),
        ("PI insurance period", "Professional indemnity insurance for twelve years after Practical Completion.",
         None, "for twelve years after Practical Completion", 0),
        ("Termination for breach", "Remedy period of twenty Working Days.", None,
         "Either party may terminate this Agreement by notice to the other", 0),
        ("Termination for insolvency", "Either party may terminate on insolvency.", None,
         "Either party may terminate this Agreement by notice to the other", 1),
        ("Removal after termination", "Tenant removes its property within ten Working Days.", None,
         "within ten Working Days and shall make good", 0),
        ("Notice by recorded delivery", "Deemed given on the second Working Day after posting.", None,
         "on the second Working Day after posting", 0),
        ("Variation estimate", "Landlord responds to a variation request within ten Working Days.", None,
         "The Landlord shall respond within ten Working Days", 0),
        ("Variation payment", "Tenant pays within twenty Working Days after demand.", None,
         "within twenty Working Days after written demand", 0),
        ("Confidentiality period", "Two years after the Lease Date or earlier termination.", None,
         "for a period of two years after the Lease Date", 0),
        ("Rent deposit release", "Third anniversary of the Lease Date.", None,
         "released on the third anniversary of the Lease Date", 0),
        ("Rent-free period", "Nine months from the Lease Date.", None, "Nine months from the Lease Date", 0),
        ("Rent review (year 6)", "First rent review in lease year 6.", "2032-07-01", "Rent review", -2),
        ("Rent review (year 11)", "Second rent review in lease year 11.", "2037-07-01", "Rent review", -1),
        ("Programme: Practical Completion inspection", "Planned for 28 and 29 June 2027.", "2027-06-28",
         "Practical Completion inspection", 0),
        ("Programme: Tenant access for data cabling", "5 May 2027 to 30 June 2027.", "2027-05-05",
         "Tenant access for data cabling", 0),
        ("Programme: Target Handover Date", "Last line of the programme.", "2027-06-30", "Target Handover Date",
         -1),
        ("Monthly progress reports", "Copies within five Working Days after receipt.", None,
         "within five Working Days after receiving it", 0),
    ]
    events, counts = [], {}
    for index, (title, description, date, trigger, where) in enumerate(spec):
        page, start, end = locate(pages, trigger, where)
        n = counts.get(trigger, 0)
        counts[trigger] = n + 1
        events.append({
            "date": date or "", "event_title": title, "event_description": description,
            "event_trigger_string": trigger,
            "persons": [{"name": LANDLORD}, {"name": TENANT}],
            "page_nr": page, "index": index, "nAppereance": n, "startIndex": start, "endIndex": end,
            "time": None,
        })
    return events


def locate(pages, trigger, where=0):
    """(page index, start, end) of one occurrence of the trigger."""
    hits = occurrences(pages, trigger)
    if not hits:
        raise SystemExit(f"Trigger not found in the generated PDF: {trigger!r}")
    if isinstance(where, int):
        return hits[where]
    anchors = occurrences(pages, where)
    if len(anchors) != 1:
        raise SystemExit(f"Anchor phrase must occur exactly once: {where!r}")
    page, a_start, a_end = anchors[0]
    return next(h for h in hits if h[0] == page and a_start <= h[1] < a_end)


def scenario_events(pages):
    """One event per positioning problem, in the PoC's own schema (1-based
    page, occurrence number on that page)."""
    def page_of(phrase, which=0):
        return occurrences(pages, phrase)[which][0] + 1

    def occurrence_on_page(phrase, which):
        hits = occurrences(pages, phrase)
        page = hits[which][0]
        return page + 1, [h for h in hits if h[0] == page].index(hits[which]) + 1

    # A long sentence that the page break cuts in two.
    spanning = None
    for title, subs in CLAUSES:
        for text in subs:
            if len(text) < 160:
                continue
            head, tail = text[:60], text[-25:]
            h, t = occurrences(pages, head), occurrences(pages, tail)
            if h and t and t[0][0] == h[0][0] + 1:
                spanning = (text, h[0][0] + 1, title.capitalize())
                break
        if spanning:
            break
    if not spanning:
        raise SystemExit("No sentence crosses a page break: change the layout and try again.")

    tp_page, tp_occ = occurrence_on_page("Either party may terminate this Agreement by notice to the other", 1)
    return [
        {"id": "evt-longstop", "title": "Longstop Date", "date": "2028-03-31",
         "description": "Unique text: found once, highlighted directly.",
         "page": page_of("If the Handover Date has not occurred by the Longstop Date"), "occurrence": 1,
         "text": "If the Handover Date has not occurred by the Longstop Date, the Tenant may terminate this "
                 "Agreement", "color": "#FFD54F"},
        {"id": "evt-termination-insolvency", "title": "Termination on insolvency", "date": None,
         "description": "The same sentence opening appears several times in the contract. The pipeline gives "
                        "the page and the occurrence number on that page.",
         "page": tp_page, "occurrence": tp_occ,
         "text": "Either party may terminate this Agreement by notice to the other", "color": "#4FC3F7"},
        {"id": "evt-delay", "title": "Rent-free extension for delay", "date": "2027-06-30",
         "description": "A defined term repeated on many pages, sent without page or occurrence number: the "
                        "surrounding text (context) picks the right one.",
         "page": None, "occurrence": None,
         "context": {"before": "the rent-free period under the Lease shall be extended by one day for each day "
                               "of delay after the", "after": "until the Handover Date"},
         "text": "Target Handover Date", "color": "#81C784"},
        {"id": "evt-page-break", "title": f"{spanning[2]} (crosses a page break)", "date": None,
         "description": "One long sentence that starts at the bottom of one page and ends on the next.",
         "page": spanning[1], "occurrence": 1, "text": spanning[0], "color": "#F48FB1"},
        {"id": "evt-warranties-paraphrased", "title": "Collateral warranties (paraphrased)", "date": None,
         "description": "The LLM paraphrased the clause: only part of its text matches the document.",
         "page": page_of("collateral warranty to the Tenant in the Agreed Form"), "occurrence": 1,
         "text": "The Landlord must make sure that the Contractor and each consultant with a design "
                 "responsibility gives a collateral warranty to the Tenant in the Agreed Form",
         "color": "#FF8A65"},
        {"id": "evt-penalty-hallucinated", "title": "Late handover penalty (hallucinated)", "date": None,
         "description": "The LLM invented this clause. The text exists nowhere in the document and there is no "
                        "fallback data, so the event is flagged as unresolved instead of highlighting the wrong "
                        "passage.",
         "page": page_of("HANDOVER DATE AND DELAY"), "occurrence": 1,
         "text": "The Landlord shall pay the Tenant a penalty of £5,000 per day of delay", "color": "#B39DDB"},
        {"id": "evt-coordinates-fallback", "title": "Signature block (coordinates only)", "date": None,
         "description": "The text does not match, but the pipeline sent coordinates: a rectangle is drawn there.",
         "page": len(pages), "occurrence": 1, "text": "Signed by the authorised signatory of the Landlord",
         "coordinates": {"left": 60, "top": 110, "width": 470, "height": 120}, "color": "#4DB6AC"},
    ]


def main():
    PDF.parent.mkdir(exist_ok=True)
    doc = SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=25 * mm, rightMargin=25 * mm, topMargin=22 * mm,
                            bottomMargin=22 * mm, title="Agreement for lease (fictitious sample)",
                            author="Sample generator")
    doc.build(build_story(), onFirstPage=footer, onLaterPages=footer)
    pages = page_texts()
    print(f"{PDF.relative_to(ROOT)}: {len(pages)} pages")
    samples = ROOT / "samples"
    (samples / "events-pipeline.json").write_text(json.dumps(pipeline_events(pages), indent=2,
                                                             ensure_ascii=False) + "\n")
    (samples / "events-scenarios.json").write_text(json.dumps({"events": scenario_events(pages)}, indent=2,
                                                              ensure_ascii=False) + "\n")
    print("samples/events-pipeline.json, samples/events-scenarios.json")


if __name__ == "__main__":
    main()
