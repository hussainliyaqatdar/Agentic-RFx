"""Builds the fabricated demo dataset: 30 canonical line items, an 8-question
quality questionnaire, last year's prices, and five vendor response sets -
each in a different messy real-world shape. Run with:

    uv run --project ../../backend python build_seed_data.py

Every vendor's quoted numbers are computed here and also written to
ground_truth.json, so the real extraction pipeline can later be scored
against a known-correct answer instead of eyeballed.
"""

import json
import random
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Font
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

random.seed(42)

ROOT = Path(__file__).resolve().parent
VENDORS_DIR = ROOT / "vendors"
FX_USD_TO_INR = 83.50
GST_PERCENT = 18
BUYER_NAME = "YoloMart"
RFX_TITLE = f"{BUYER_NAME} - Corrugated Packaging RFx (FY2026)"

# ---------------------------------------------------------------------------
# Canonical line items - 22 popular corrugated packaging SKUs + 8 specialty
# SKUs of the kind an Amazon/Walmart-grade packaging supplier carries.
# ---------------------------------------------------------------------------

LINE_ITEMS = [
    # sku, description, category, ply, flute, dims_mm, gsm, printed, weight_kg, qty, unit, ref_price_inr
    ("PKG-101", "3-ply RSC box, B-flute, 200x150x100mm, plain kraft", "plain_rsc_3ply", 3, "B", "200x150x100", 120, False, 0.12, 5000, "box", 14.50),
    ("PKG-102", "3-ply RSC box, B-flute, 300x200x150mm, plain kraft", "plain_rsc_3ply", 3, "B", "300x200x150", 120, False, 0.22, 4000, "box", 22.00),
    ("PKG-103", "3-ply RSC box, B-flute, 400x300x200mm, plain kraft", "plain_rsc_3ply", 3, "B", "400x300x200", 140, False, 0.38, 3000, "box", 34.00),
    ("PKG-104", "3-ply RSC box, C-flute, 300x250x200mm, plain kraft", "plain_rsc_3ply", 3, "C", "300x250x200", 140, False, 0.36, 3000, "box", 33.00),
    ("PKG-105", "3-ply RSC box, C-flute, 450x350x250mm, plain kraft", "plain_rsc_3ply", 3, "C", "450x350x250", 150, False, 0.55, 2000, "box", 48.00),
    ("PKG-106", "5-ply RSC box, BC-flute, 400x300x300mm, plain kraft", "plain_rsc_5ply", 5, "BC", "400x300x300", 180, False, 0.62, 2500, "box", 58.00),
    ("PKG-107", "5-ply RSC box, BC-flute, 500x400x350mm, plain kraft", "plain_rsc_5ply", 5, "BC", "500x400x350", 180, False, 0.85, 2000, "box", 76.00),
    ("PKG-108", "5-ply RSC box, BC-flute, 600x450x400mm, plain kraft", "plain_rsc_5ply", 5, "BC", "600x450x400", 200, False, 1.10, 1500, "box", 98.00),
    ("PKG-109", "5-ply RSC box, BC-flute, 350x350x350mm cube, plain kraft", "plain_rsc_5ply", 5, "BC", "350x350x350", 180, False, 0.68, 1800, "box", 62.00),
    ("PKG-110", "3-ply RSC box, B-flute, 250x200x150mm, 1-colour print", "printed_3ply", 3, "B", "250x200x150", 130, True, 0.24, 3500, "box", 26.00),
    ("PKG-111", "3-ply RSC box, B-flute, 350x250x200mm, 1-colour print", "printed_3ply", 3, "B", "350x250x200", 130, True, 0.40, 2500, "box", 39.00),
    ("PKG-112", "5-ply RSC box, BC-flute, 450x350x300mm, 2-colour print", "printed_5ply", 5, "BC", "450x350x300", 190, True, 0.70, 2000, "box", 72.00),
    ("PKG-113", "5-ply RSC box, BC-flute, 500x500x400mm, 2-colour print", "printed_5ply", 5, "BC", "500x500x400", 190, True, 0.95, 1500, "box", 92.00),
    ("PKG-114", "3-ply document/file box, B-flute, 320x260x140mm, plain kraft", "doc_mailer", 3, "B", "320x260x140", 125, False, 0.26, 4000, "box", 24.00),
    ("PKG-115", "3-ply mailer box, B-flute, 300x230x100mm, plain kraft", "doc_mailer", 3, "B", "300x230x100", 130, False, 0.20, 6000, "box", 19.50),
    ("PKG-116", "5-ply heavy carton, BC-flute, 550x400x350mm, plain kraft", "heavy_5ply", 5, "BC", "550x400x350", 210, False, 1.05, 1200, "box", 105.00),
    ("PKG-117", "5-ply heavy carton, BC-flute, 600x500x450mm, plain kraft", "heavy_5ply", 5, "BC", "600x500x450", 220, False, 1.35, 1000, "box", 128.00),
    ("PKG-118", "3-ply small parts box, B-flute, 150x100x100mm, plain kraft", "small_parts_3ply", 3, "B", "150x100x100", 110, False, 0.08, 8000, "box", 9.50),
    ("PKG-119", "3-ply small parts box, B-flute, 200x150x150mm, plain kraft", "small_parts_3ply", 3, "B", "200x150x150", 110, False, 0.13, 7000, "box", 13.00),
    ("PKG-120", "5-ply bulk carton, BC-flute, 650x450x400mm, plain kraft", "heavy_5ply", 5, "BC", "650x450x400", 220, False, 1.45, 900, "box", 138.00),
    ("PKG-121", "3-ply flat-pack die-cut sheet, B-flute, 400x300mm", "flatpack_3ply", 3, "B", "400x300", 140, False, 0.18, 5000, "sheet", 16.00),
    ("PKG-122", "5-ply flat-pack die-cut sheet, BC-flute, 500x400mm", "flatpack_5ply", 5, "BC", "500x400", 190, False, 0.32, 3000, "sheet", 29.00),
    # Specialty - the kind of SKU an Amazon/Walmart-grade packaging supplier carries
    ("PKG-201", "E-commerce self-locking mailer box, C-flute, 350x250x100mm, 1-colour brand print, auto-bottom lock", "specialty", 3, "C", "350x250x100", 150, True, 0.28, 10000, "box", 32.00),
    ("PKG-202", "Automated case-erector RSC, 5-ply BC-flute, 500x350x300mm, packline-compatible (+/-1mm glue-flap tolerance)", "specialty", 5, "BC", "500x350x300", 190, False, 0.80, 6000, "box", 89.00),
    ("PKG-203", "Retail-ready packaging tray with perforated tear-strip, 3-ply B-flute, 400x300x150mm, printed", "specialty", 3, "B", "400x300x150", 150, True, 0.42, 4000, "box", 46.00),
    ("PKG-204", "Pallet corner boards / edge protectors, 2mm triple-wall, 50x50x1000mm L-profile", "specialty", 3, "-", "50x50x1000", 300, False, 0.30, 2000, "piece", 38.00),
    ("PKG-205", "Void-fill dunnage pad, honeycomb corrugated, 300x300x20mm", "specialty", 1, "-", "300x300x20", 90, False, 0.05, 15000, "piece", 6.50),
    ("PKG-206", "Insulated cold-chain box with EPE liner, 5-ply BC-flute, 400x300x300mm", "specialty", 5, "BC", "400x300x300", 200, False, 0.95, 1500, "box", 145.00),
    ("PKG-207", "Heavy-duty export carton, 7-ply triple-wall, 600x500x500mm, ECT-48 rated", "specialty", 7, "BC/BC", "600x500x500", 280, False, 2.10, 500, "box", 320.00),
    ("PKG-208", "Custom die-cut POS display box, 3-ply B-flute, 500x400x600mm, full-colour litho-laminated print", "specialty", 3, "B", "500x400x600", 160, True, 0.75, 800, "box", 210.00),
]

REFERENCE_PERIOD = "FY2025"

LINE_ITEM_DICTS = [
    {
        "line_no": i + 1,
        "sku_code": sku,
        "description": desc,
        "category": category,
        "spec_attributes": {
            "ply": ply, "flute": flute, "dimensions_mm": dims, "gsm": gsm,
            "printed": printed, "weight_kg": weight_kg,
        },
        "quantity": qty,
        "unit": unit,
        "reference_unit_price": ref_price,
        "reference_currency": "INR",
        "reference_period_label": REFERENCE_PERIOD,
    }
    for i, (sku, desc, category, ply, flute, dims, gsm, printed, weight_kg, qty, unit, ref_price)
    in enumerate(LINE_ITEMS)
]
LI_BY_SKU = {li["sku_code"]: li for li in LINE_ITEM_DICTS}


def by_category(*cats):
    return [li for li in LINE_ITEM_DICTS if li["category"] in cats]


# ---------------------------------------------------------------------------
# Quality questionnaire
# ---------------------------------------------------------------------------

QUESTIONNAIRE = [
    {"question_no": 1, "question_type": "yes_no", "question_text": "Are you ISO 9001:2015 certified for quality management?"},
    {"question_no": 2, "question_type": "yes_no", "question_text": "Do you hold FSC or PEFC chain-of-custody certification for board sourcing?"},
    {"question_no": 3, "question_type": "number", "question_text": "What is your average manufacturing defect/reject rate, as a percentage of units produced?"},
    {"question_no": 4, "question_type": "choice", "question_text": "Do you edge-crush-test (ECT) or burst-strength-test every production batch, only sample batches, or not at all?", "choices": ["every_batch", "sample_batches", "not_tested"]},
    {"question_no": 5, "question_type": "number", "question_text": "What percentage of recycled fibre content is used in your board?"},
    {"question_no": 6, "question_type": "yes_no", "question_text": "Have you passed an Amazon Packaging Certification (APASS) or equivalent retailer packaging audit in the last 24 months?"},
    {"question_no": 7, "question_type": "number", "question_text": "What is your standard lead time, in days, for a repeat order of this size?"},
    {"question_no": 8, "question_type": "yes_no", "question_text": "Do you provide a certificate of conformance with each shipment?"},
]
Q_BY_NO = {q["question_no"]: q for q in QUESTIONNAIRE}

# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------

VENDORS = [
    {
        "slug": "vendor_a_apex",
        "name": "Apex Packaging Solutions",
        "contact_email": "sales@apexpack.example",
        "persona_notes": "Compliant happy-path vendor. Fills the buyer's own Excel template exactly; questionnaire answered separately as a clean Word doc.",
    },
    {
        "slug": "vendor_b_shreeji",
        "name": "Shreeji Corrugators",
        "contact_email": "quotes@shreejicorr.example",
        "persona_notes": "Sends their own differently-structured Excel (own codes, own column order, GST column). Questionnaire answered in prose inside the covering email.",
    },
    {
        "slug": "vendor_c_globalcorrfab",
        "name": "Global Corrfab Ltd.",
        "contact_email": "export@globalcorrfab.example",
        "persona_notes": "Export-oriented. Formal letterhead PDF quoted in USD with an 8% volume discount buried in a footnote and the questionnaire embedded at the end; freight/payment terms only exist in a separate follow-up email.",
    },
    {
        "slug": "vendor_d_suretypack",
        "name": "Suretypack Industries",
        "contact_email": "info@suretypack.example",
        "persona_notes": "Smaller regional vendor. One Word doc holds both the quote (prose-heavy, prices embedded in paragraphs) and the questionnaire (2 questions left unanswered). Quotes 27/30 lines and prices two SKUs per 100 pieces instead of per box. Not ISO certified.",
    },
    {
        "slug": "vendor_e_balaji",
        "name": "Balaji Package Traders",
        "contact_email": "balajipkg@example.com",
        "persona_notes": "Very informal trader. An earlier photo of a printed rate card (angled) is superseded by a terser follow-up email with blanket per-kg rates plus 'rest same as last year'. Only 3 of 8 questionnaire questions answered, tersely, in the same email. Doesn't cover specialty SKUs at all.",
    },
]


def mult(lo, hi):
    return random.uniform(lo, hi)


def round_to(value, step):
    return round(round(value / step) * step, 2)


# ---------------------------------------------------------------------------
# Ground truth - vendor A (clean, full coverage)
# ---------------------------------------------------------------------------

def build_vendor_a():
    lines = []
    for li in LINE_ITEM_DICTS:
        price = round_to(li["reference_unit_price"] * mult(0.97, 1.04), 0.10)
        lines.append({
            "sku_code": li["sku_code"],
            "vendor_description": li["description"],
            "quantity": li["quantity"],
            "unit": li["unit"],
            "unit_price": price,
            "currency": "INR",
            "lead_time_days": 12,
            "notes": None,
        })
    answers = {1: "Yes", 2: "Yes (FSC-C123456)", 3: "0.3", 4: "every_batch", 5: "35", 6: "Yes", 7: "12", 8: "Yes"}
    return lines, answers


# ---------------------------------------------------------------------------
# Ground truth - vendor B (own template, full coverage, prose questionnaire)
# ---------------------------------------------------------------------------

def build_vendor_b():
    lines = []
    for idx, li in enumerate(LINE_ITEM_DICTS, start=1):
        price = round_to(li["reference_unit_price"] * mult(0.90, 1.15), 0.50)
        spec = li["spec_attributes"]
        kind = "Printed" if spec["printed"] else "Plain"
        own_desc = f"{spec['ply']}Ply {kind} Carton {spec['dimensions_mm']}mm"
        remark = None
        if li["category"] == "specialty":
            remark = "Subject to board availability, please confirm before order"
        lines.append({
            "sku_code": li["sku_code"],
            "vendor_code": f"SJ-{idx:03d}",
            "vendor_description": own_desc,
            "quantity": li["quantity"],
            "unit": li["unit"],
            "unit_price": price,
            "currency": "INR",
            "gst_percent": GST_PERCENT,
            "lead_time_days": 18,
            "notes": remark,
        })
    answers = {1: "Yes", 2: "No", 3: "1.2", 4: "sample_batches", 5: "20", 6: "No", 7: "18", 8: "Yes"}
    return lines, answers


# ---------------------------------------------------------------------------
# Ground truth - vendor C (USD, footnote discount, split PDF/email)
# ---------------------------------------------------------------------------

VENDOR_C_DISCOUNT_THRESHOLD = 2000
VENDOR_C_DISCOUNT_PCT = 8


def build_vendor_c():
    lines = []
    for li in LINE_ITEM_DICTS:
        list_price_usd = round(li["reference_unit_price"] * mult(1.05, 1.20) / FX_USD_TO_INR, 2)
        lines.append({
            "sku_code": li["sku_code"],
            "vendor_description": li["description"],
            "quantity": li["quantity"],
            "unit": li["unit"],
            "list_unit_price": list_price_usd,
            "currency": "USD",
            "discount_applies": li["quantity"] > VENDOR_C_DISCOUNT_THRESHOLD,
            "discount_percent": VENDOR_C_DISCOUNT_PCT,
        })
    answers = {1: "Yes", 2: "Yes (FSC and PEFC)", 3: "0.25", 4: "every_batch", 5: "40", 6: "Yes", 7: "21", 8: "Yes"}
    return lines, answers


# ---------------------------------------------------------------------------
# Ground truth - vendor D (prose Word doc, 27/30 lines, per-100 units)
# ---------------------------------------------------------------------------

VENDOR_D_SKIPPED = {"PKG-202", "PKG-204", "PKG-206"}
VENDOR_D_PER_100 = {"PKG-118", "PKG-119"}


def build_vendor_d():
    lines = []
    for li in LINE_ITEM_DICTS:
        if li["sku_code"] in VENDOR_D_SKIPPED:
            continue
        price = round_to(li["reference_unit_price"] * mult(0.85, 0.98), 0.50)
        if li["sku_code"] in VENDOR_D_PER_100:
            unit = "100 pieces"
            unit_price = round_to(price * 100 * 0.97, 1.0)  # slight bulk-pack discount
        else:
            unit = li["unit"]
            unit_price = price
        lines.append({
            "sku_code": li["sku_code"],
            "vendor_description": li["description"],
            "quantity": li["quantity"],
            "unit": unit,
            "unit_price": unit_price,
            "currency": "INR",
            "lead_time_days": 15,
        })
    # 2 questions deliberately left unanswered: defect rate (3) and recycled content (5)
    answers = {1: "No", 2: "No", 4: "sample_batches", 6: "No", 7: "15", 8: "No"}
    return lines, answers


# ---------------------------------------------------------------------------
# Ground truth - vendor E (photo superseded by terse email, sparse coverage)
# ---------------------------------------------------------------------------

VENDOR_E_RATE_5PLY_PER_KG = 42.0
VENDOR_E_RATE_3PLY_PER_KG = 38.0
# Earlier photo (superseded): different, slightly higher category rates
VENDOR_E_PHOTO_RATES = {
    "3-Ply Small (up to 250mm)": 40.0,
    "3-Ply Large (above 250mm)": 36.0,
    "5-Ply Small (up to 400mm)": 44.0,
    "5-Ply Large (above 400mm)": 40.0,
}


def build_vendor_e():
    lines = []
    for li in by_category("plain_rsc_3ply"):
        rate = VENDOR_E_RATE_3PLY_PER_KG
        unit_price = round_to(rate * li["spec_attributes"]["weight_kg"], 0.50)
        lines.append({"sku_code": li["sku_code"], "quantity": li["quantity"], "unit": li["unit"],
                       "unit_price": unit_price, "currency": "INR", "source": "email_blanket_rate",
                       "note": f"{rate}/kg x {li['spec_attributes']['weight_kg']}kg"})
    for li in by_category("plain_rsc_5ply"):
        rate = VENDOR_E_RATE_5PLY_PER_KG
        unit_price = round_to(rate * li["spec_attributes"]["weight_kg"], 0.50)
        lines.append({"sku_code": li["sku_code"], "quantity": li["quantity"], "unit": li["unit"],
                       "unit_price": unit_price, "currency": "INR", "source": "email_blanket_rate",
                       "note": f"{rate}/kg x {li['spec_attributes']['weight_kg']}kg"})
    fallback_categories = ("printed_3ply", "printed_5ply", "doc_mailer", "heavy_5ply", "small_parts_3ply", "flatpack_3ply", "flatpack_5ply")
    for li in by_category(*fallback_categories):
        lines.append({"sku_code": li["sku_code"], "quantity": li["quantity"], "unit": li["unit"],
                       "unit_price": li["reference_unit_price"], "currency": "INR", "source": "same_as_last_year",
                       "note": f"vendor said 'rest same as last year' -> {REFERENCE_PERIOD} reference price"})
    # specialty items: not mentioned at all - true gap, not even a "same as last year" fallback
    answers = {1: "Yes", 7: "7-10 days", 8: "No"}
    return lines, answers


VENDOR_BUILDERS = {
    "vendor_a_apex": build_vendor_a,
    "vendor_b_shreeji": build_vendor_b,
    "vendor_c_globalcorrfab": build_vendor_c,
    "vendor_d_suretypack": build_vendor_d,
    "vendor_e_balaji": build_vendor_e,
}

# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_vendor_a(vendor_dir, lines, answers):
    vendor_dir.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Quote"
    headers = ["Line No", "SKU Code", "Description", "Quantity", "Unit", "Unit Price (INR)", "Lead Time (days)", "Notes"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for i, line in enumerate(lines, start=1):
        li = LI_BY_SKU[line["sku_code"]]
        ws.append([i, line["sku_code"], line["vendor_description"], line["quantity"], line["unit"],
                   line["unit_price"], line["lead_time_days"], line["notes"] or ""])
    for col, width in zip("ABCDEFGH", (8, 10, 46, 10, 8, 16, 16, 20)):
        ws.column_dimensions[col].width = width
    wb.save(vendor_dir / "quote.xlsx")

    doc = Document()
    doc.add_heading("Quality Questionnaire Response", level=1)
    doc.add_paragraph(f"Apex Packaging Solutions  |  Prepared for: {BUYER_NAME}  |  RFx: Corrugated Packaging FY2026")
    for q in QUESTIONNAIRE:
        p = doc.add_paragraph()
        run = p.add_run(f"Q{q['question_no']}. {q['question_text']}")
        run.bold = True
        doc.add_paragraph(answers[q["question_no"]])
    doc.save(vendor_dir / "questionnaire.docx")


def render_vendor_b(vendor_dir, lines, answers):
    vendor_dir.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Shreeji Quotation"
    headers = ["S.No", "Our Product Code", "Item Description", "Pack Qty", "Rate per Unit (INR)", "GST %", "Remarks"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for i, line in enumerate(lines, start=1):
        ws.append([i, line["vendor_code"], line["vendor_description"], line["quantity"],
                   line["unit_price"], line["gst_percent"], line["notes"] or ""])
    for col, width in zip("ABCDEFG", (6, 14, 34, 10, 16, 8, 36)):
        ws.column_dimensions[col].width = width
    wb.save(vendor_dir / "quote.xlsx")

    answer_prose = (
        f"Dear {BUYER_NAME} Procurement Team,\n\n"
        f"Please find attached our quotation SJ-Q-2201 for the corrugated packaging items in your RFx. "
        f"Rates are ex-factory, GST extra as shown, validity 30 days.\n\n"
        f"Regarding the queries in your questionnaire - yes we are ISO 9001 certified (cert available on request), "
        f"but we do not currently hold FSC or PEFC certification for our board sourcing. Our rejection rate runs "
        f"about {answers[3]}% on average and we test on a sample-batch basis, not every batch. Recycled fibre "
        f"content is roughly {answers[5]}%. We have not gone through an Amazon APASS audit. Standard lead time "
        f"is {answers[7]} working days from PO, and yes, we send a certificate of conformance with every dispatch.\n\n"
        f"Please let us know if any sizes need revision.\n\n"
        f"Regards,\nShreeji Corrugators - Sales Desk"
    )
    (vendor_dir / "cover_email.txt").write_text(
        "From: quotes@shreejicorr.example\nSubject: RE: RFx - Corrugated Packaging - Shreeji Quotation\n\n" + answer_prose,
        encoding="utf-8",
    )


def render_vendor_c(vendor_dir, lines, answers):
    vendor_dir.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Title"], fontSize=16, spaceAfter=2)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    footnote_style = ParagraphStyle("Footnote", parent=styles["Normal"], fontSize=7.5, textColor=colors.grey, spaceBefore=6)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=11, spaceBefore=14)

    story = [
        Paragraph("GLOBAL CORRFAB LTD.", header_style),
        Paragraph("Plot 42, Export Promotion Industrial Park, Mundra SEZ, Gujarat 370421, India &nbsp;|&nbsp; export@globalcorrfab.example &nbsp;|&nbsp; GSTIN 24AAGCG1234F1Z5", sub_style),
        Spacer(1, 10 * mm),
        Paragraph(f"To: {BUYER_NAME}, Procurement Team", styles["Normal"]),
        Paragraph("QUOTATION - RFx: Corrugated Packaging FY2026", styles["Heading2"]),
        Spacer(1, 4 * mm),
    ]

    table_data = [["SKU", "Description", "Qty", "Unit", "List Price (USD)"]]
    for line in lines:
        li = LI_BY_SKU[line["sku_code"]]
        table_data.append([line["sku_code"], Paragraph(li["description"], styles["Normal"]), str(line["quantity"]),
                            line["unit"], f"${line['list_unit_price']:.2f}"])
    table = Table(table_data, colWidths=[45, 210, 40, 40, 75], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
    ]))
    story.append(table)
    story.append(Paragraph(
        f"* Prices shown are standard list rates. A {VENDOR_C_DISCOUNT_PCT}% volume discount applies to any "
        f"single line item with an order quantity exceeding {VENDOR_C_DISCOUNT_THRESHOLD:,} units, applied at "
        f"the time of invoicing.",
        footnote_style,
    ))

    story.append(Paragraph("Quality Questionnaire Response", section_style))
    for q in QUESTIONNAIRE:
        story.append(Paragraph(f"<b>Q{q['question_no']}.</b> {q['question_text']}", styles["Normal"]))
        story.append(Paragraph(answers[q["question_no"]], styles["Normal"]))
        story.append(Spacer(1, 2 * mm))

    SimpleDocTemplate(str(vendor_dir / "quote.pdf"), pagesize=A4,
                       leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm).build(story)

    (vendor_dir / "followup_email.txt").write_text(
        "From: export@globalcorrfab.example\n"
        "Subject: RE: RFx - Corrugated Packaging - commercial terms\n\n"
        f"Hi {BUYER_NAME} team,\n\n"
        "Following up on our quotation (attached separately as PDF) with the commercial terms that aren't on "
        "the formal document:\n\n"
        "- Payment: 30% advance, balance 70% against B/L copy\n"
        "- Freight: extra, FOB Mundra Port - buyer to arrange last-mile from port of discharge\n"
        "- Lead time: 21 days ex-works from PO confirmation (please note this is ex-works; add transit time "
        "separately)\n"
        "- Quote validity: 45 days\n\n"
        "Let us know if you need anything else.\n\n"
        "Best,\nExport Sales - Global Corrfab Ltd.",
        encoding="utf-8",
    )


CATEGORY_LABELS = {
    "plain_rsc_3ply": "the standard single-wall 3-ply cartons",
    "plain_rsc_5ply": "the 5-ply double-wall cartons",
    "printed_3ply": "the printed 3-ply cartons",
    "printed_5ply": "the printed 5-ply cartons",
    "doc_mailer": "the document and mailer boxes",
    "heavy_5ply": "the heavier 5-ply cartons",
    "flatpack_3ply": "the 3-ply flat-pack sheets",
    "flatpack_5ply": "the 5-ply flat-pack sheets",
    "specialty": "the specialty items",
}


def render_vendor_d(vendor_dir, lines, answers):
    vendor_dir.mkdir(parents=True, exist_ok=True)
    lines_by_sku = {l["sku_code"]: l for l in lines}
    doc = Document()
    doc.add_heading("Suretypack Industries - Quotation & Questionnaire", level=1)
    doc.add_paragraph(
        f"Dear {BUYER_NAME} Procurement Team, thank you for the opportunity to quote on your corrugated "
        "packaging requirement. "
        "Please find our pricing below, grouped by carton type for ease of reading. All rates are per box "
        "unless stated otherwise, ex-factory Bhiwandi, GST as applicable. We are unable to quote for the "
        "automated case-erector cartons (tolerance beyond our current tooling), the pallet corner boards, "
        "or the insulated cold-chain boxes this time around - happy to explore these in a future round."
    )

    def price_of(sku):
        return lines_by_sku[sku]["unit_price"] if sku in lines_by_sku else None

    para_groups = [
        ("plain_rsc_3ply", "For {label}, our rates work out to: " + ", ".join(
            f"{li['spec_attributes']['dimensions_mm']}mm at Rs.{{p{li['sku_code']}}}/box"
            for li in by_category("plain_rsc_3ply")) + "."),
        ("plain_rsc_5ply", "On {label}, we've priced the " + ", ".join(
            f"{li['spec_attributes']['dimensions_mm']}mm size at Rs.{{p{li['sku_code']}}}/box"
            for li in by_category("plain_rsc_5ply")) + "."),
        ("printed_3ply", "For {label} (1-colour), the 250x200x150mm comes to Rs.{p" + "PKG-110" + "}/box and the "
         "350x250x200mm to Rs.{p" + "PKG-111" + "}/box."),
        ("printed_5ply", "{label} (2-colour) are priced at Rs.{p" + "PKG-112" + "}/box for the 450x350x300mm and "
         "Rs.{p" + "PKG-113" + "}/box for the 500x500x400mm."),
        ("doc_mailer", "For {label}, the document box is Rs.{p" + "PKG-114" + "}/box and the mailer box is "
         "Rs.{p" + "PKG-115" + "}/box."),
        ("heavy_5ply", "{label}: 550x400x350mm at Rs.{p" + "PKG-116" + "}/box, 600x500x450mm at Rs.{p" + "PKG-117" +
         "}/box, and the 650x450x400mm bulk carton at Rs.{p" + "PKG-120" + "}/box."),
    ]
    for category, template in para_groups:
        text = template.format(label=CATEGORY_LABELS[category], **{f"p{sku}": price_of(sku) for sku in lines_by_sku})
        doc.add_paragraph(text)

    doc.add_paragraph(
        f"For the small parts boxes, we price by the 100: the 150x100x100mm works out to "
        f"Rs.{price_of('PKG-118')} per 100 pieces, and the 200x150x150mm to Rs.{price_of('PKG-119')} per 100 "
        f"pieces (not per box, given the smaller size these are usually ordered in bulk packs)."
    )
    specialty_present = [s for s in ("PKG-201", "PKG-203", "PKG-205", "PKG-207", "PKG-208") if s in lines_by_sku]
    specialty_text = "; ".join(f"{LI_BY_SKU[s]['description'].split(',')[0]} at Rs.{price_of(s)}/{lines_by_sku[s]['unit']}" for s in specialty_present)
    doc.add_paragraph(f"On the specialty items we can supply: {specialty_text}.")
    doc.add_paragraph(
        f"For the flat-pack die-cut sheets: 3-ply at Rs.{price_of('PKG-121')}/sheet and 5-ply at "
        f"Rs.{price_of('PKG-122')}/sheet."
    )
    doc.add_paragraph(
        "Commercial terms: 40% advance with PO, balance on delivery. Lead time 15 days from PO. Freight extra, "
        "to be billed at actuals. Quote valid for 21 days."
    )

    doc.add_heading("Quality Questionnaire", level=2)
    for q in QUESTIONNAIRE:
        p = doc.add_paragraph()
        run = p.add_run(f"Q{q['question_no']}. {q['question_text']}")
        run.bold = True
        if q["question_no"] in answers:
            doc.add_paragraph(answers[q["question_no"]])
        # questions 3 and 5 intentionally left with no answer paragraph at all
    doc.save(vendor_dir / "quote_and_questionnaire.docx")


def _load_font(size):
    for name in ("cour.ttf", "arial.ttf", "consola.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_vendor_e(vendor_dir, lines, answers):
    vendor_dir.mkdir(parents=True, exist_ok=True)

    width, height = 900, 700
    card = Image.new("RGB", (width, height), "#fdfdf5")
    draw = ImageDraw.Draw(card)
    title_font = _load_font(30)
    row_font = _load_font(22)

    draw.text((40, 30), "BALAJI PACKAGE TRADERS", font=title_font, fill="#111111")
    draw.text((40, 70), "Rate Card - Corrugated Boxes (per kg)", font=row_font, fill="#333333")
    draw.line((40, 110, 860, 110), fill="#111111", width=2)

    y = 150
    for label, rate in VENDOR_E_PHOTO_RATES.items():
        draw.text((60, y), f"{label}", font=row_font, fill="#111111")
        draw.text((640, y), f"Rs. {rate:.0f} / kg", font=row_font, fill="#111111")
        y += 55
    draw.line((40, y + 10, 860, y + 10), fill="#111111", width=1)
    draw.text((40, y + 30), "Freight extra. Prices subject to change without notice.", font=_load_font(18), fill="#555555")
    draw.text((40, y + 60), "Contact: 98xxxxxx10", font=_load_font(18), fill="#555555")

    rotated = card.rotate(9, expand=True, fillcolor="#e5e5df")
    rotated = rotated.filter(ImageFilter.GaussianBlur(0.6))
    canvas = Image.new("RGB", (rotated.width + 80, rotated.height + 80), "#c9c9bd")
    canvas.paste(rotated, (40, 40))
    canvas = canvas.convert("RGB")
    canvas.save(vendor_dir / "rate_card_photo.jpg", quality=72)

    answered_lines = []
    if 1 in answers:
        answered_lines.append(f"ISO - {answers[1]}")
    if 7 in answers:
        answered_lines.append(f"lead time - {answers[7]}")
    if 8 in answers:
        answered_lines.append(f"CoC with shipment - {answers[8]}")
    (vendor_dir / "followup_email.txt").write_text(
        "From: balajipkg@example.com\n"
        f"Subject: rates - {BUYER_NAME}\n\n"
        "sir, rate card attached from last week but pls note update -\n\n"
        f"Rs.{VENDOR_E_RATE_5PLY_PER_KG:.0f}/kg for the 5-ply, {VENDOR_E_RATE_3PLY_PER_KG:.0f} for the 3-ply - "
        "this is for our plain standard boxes only, not the printed ones, document/mailer boxes, heavy "
        "cartons, small parts boxes or flat sheets. for all of those, rest same as last year. we don't do "
        "the special/custom stuff - POS boxes, cold chain, export cartons, RRP trays, corner boards, "
        "e-commerce mailers etc - so no rate for those from us, sorry sir.\n\n"
        "freight extra.\n\n"
        "for your questions - " + "; ".join(answered_lines) + ". other details will send separately.\n\n"
        "balaji pkg",
        encoding="utf-8",
    )


RENDERERS = {
    "vendor_a_apex": render_vendor_a,
    "vendor_b_shreeji": render_vendor_b,
    "vendor_c_globalcorrfab": render_vendor_c,
    "vendor_d_suretypack": render_vendor_d,
    "vendor_e_balaji": render_vendor_e,
}


RFX_META = {
    "buyer_name": BUYER_NAME,
    "title": RFX_TITLE,
    "category": "Corrugated Packaging",
    "scope_description": (
        f"{BUYER_NAME} needs 30 line items of corrugated packaging for its fulfilment centres - "
        "standard cartons plus e-commerce/retail-ready specialty items - sourced from 5 vendors."
    ),
    "canonical_currency": "INR",
    # What YoloMart is asking for - each vendor's own proposed terms (in their quote/email) are
    # compared against this, not assumed to match it.
    "payment_terms": "Net 30 from delivery",
    "delivery_terms": "DAP, YoloMart fulfilment centre, Bhiwandi, Maharashtra",
    "validity_days": 30,
    # Reference FX rate for converting any non-INR vendor quote (e.g. Global Corrfab's USD
    # pricing) to the canonical currency. Static by design - see project README.
    "fx_rates": {"USD_INR": FX_USD_TO_INR},
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "rfx.json").write_text(json.dumps(RFX_META, indent=2), encoding="utf-8")
    (ROOT / "line_items.json").write_text(json.dumps(LINE_ITEM_DICTS, indent=2), encoding="utf-8")
    (ROOT / "questionnaire.json").write_text(json.dumps(QUESTIONNAIRE, indent=2), encoding="utf-8")
    (ROOT / "vendors.json").write_text(json.dumps(VENDORS, indent=2), encoding="utf-8")

    historical = [
        {"sku_code": li["sku_code"], "unit_price": li["reference_unit_price"], "currency": "INR",
         "unit": li["unit"], "period_label": li["reference_period_label"]}
        for li in LINE_ITEM_DICTS
    ]
    (ROOT / "historical_prices.json").write_text(json.dumps(historical, indent=2), encoding="utf-8")

    ground_truth = {}
    for vendor in VENDORS:
        slug = vendor["slug"]
        lines, answers = VENDOR_BUILDERS[slug]()
        ground_truth[slug] = {
            "vendor_name": vendor["name"],
            "line_count_quoted": len(lines),
            "lines": lines,
            "answers": {str(k): v for k, v in answers.items()},
        }
        RENDERERS[slug](VENDORS_DIR / slug, lines, answers)
        print(f"{slug}: {len(lines)}/{len(LINE_ITEM_DICTS)} lines, {len(answers)}/{len(QUESTIONNAIRE)} questions answered")

    (VENDORS_DIR / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    print("\nDone. Files written under", ROOT)


if __name__ == "__main__":
    main()
