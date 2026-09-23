from sqlmodel import Session, select

from app.models import (
    ExtractedAnswer,
    ExtractedLineQuote,
    Rfx,
    RfxLineItem,
    RfxQuestion,
    RfxVendor,
    Vendor,
)


def build_comparison_data(session: Session, rfx_id: int) -> dict:
    """The MxN grid: every line item x every vendor. Shared by the comparison
    endpoint and the analyst agent's context builder, so there's exactly one
    place that knows how to join ExtractedLineQuote back to line items."""
    line_items = session.exec(
        select(RfxLineItem).where(RfxLineItem.rfx_id == rfx_id).order_by(RfxLineItem.line_no)
    ).all()
    rfx_vendors = session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx_id)).all()
    vendor_by_id = {}
    if rfx_vendors:
        for v in session.exec(select(Vendor).where(Vendor.id.in_([rv.vendor_id for rv in rfx_vendors]))).all():
            vendor_by_id[v.id] = v

    quotes_by_key: dict[tuple[int, int], ExtractedLineQuote] = {}
    if rfx_vendors:
        rfx_vendor_ids = [rv.id for rv in rfx_vendors]
        for q in session.exec(
            select(ExtractedLineQuote).where(ExtractedLineQuote.rfx_vendor_id.in_(rfx_vendor_ids))
        ).all():
            if q.rfx_line_item_id is not None:
                quotes_by_key[(q.rfx_vendor_id, q.rfx_line_item_id)] = q

    vendor_columns = [
        {"rfx_vendor_id": rv.id, "vendor_id": rv.vendor_id, "name": vendor_by_id[rv.vendor_id].name,
         "response_status": rv.response_status}
        for rv in rfx_vendors if rv.vendor_id in vendor_by_id
    ]

    rows = []
    for li in line_items:
        cells = {}
        for rv in rfx_vendors:
            quote = quotes_by_key.get((rv.id, li.id))
            cells[str(rv.id)] = None if quote is None else {
                "unit_price_normalized": quote.unit_price_normalized,
                "currency_normalized": quote.currency_normalized,
                "extraction_confidence": quote.extraction_confidence,
                "match_confidence": quote.match_confidence,
                "needs_review": quote.needs_review,
                "conversion_notes": quote.conversion_notes,
                "source_citation": quote.source_citation,
                "vendor_raw_description": quote.vendor_raw_description,
                "lead_time_days": quote.lead_time_days,
                "evaluator_verdict": quote.evaluator_verdict,
                "evaluator_reasoning": quote.evaluator_reasoning,
            }
        rows.append({
            "line_item_id": li.id,
            "line_no": li.line_no,
            "sku_code": li.sku_code,
            "description": li.description,
            "spec_attributes": li.spec_attributes,
            "quantity": li.quantity,
            "unit": li.unit,
            "cells": cells,
        })

    return {"vendors": vendor_columns, "rows": rows}


def build_questionnaire_data(session: Session, rfx_id: int) -> dict:
    """Every vendor's answer to every question, for the analyst agent's
    compliance reasoning and the vendor detail drawer."""
    questions = session.exec(
        select(RfxQuestion).where(RfxQuestion.rfx_id == rfx_id).order_by(RfxQuestion.question_no)
    ).all()
    rfx_vendors = session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx_id)).all()
    vendor_by_id = {}
    if rfx_vendors:
        for v in session.exec(select(Vendor).where(Vendor.id.in_([rv.vendor_id for rv in rfx_vendors]))).all():
            vendor_by_id[v.id] = v

    answers_by_key: dict[tuple[int, int], ExtractedAnswer] = {}
    if rfx_vendors:
        rfx_vendor_ids = [rv.id for rv in rfx_vendors]
        for a in session.exec(
            select(ExtractedAnswer).where(ExtractedAnswer.rfx_vendor_id.in_(rfx_vendor_ids))
        ).all():
            answers_by_key[(a.rfx_vendor_id, a.rfx_question_id)] = a

    vendors = []
    for rv in rfx_vendors:
        if rv.vendor_id not in vendor_by_id:
            continue
        answers = []
        for q in questions:
            a = answers_by_key.get((rv.id, q.id))
            answers.append({
                "question_no": q.question_no,
                "question_text": q.question_text,
                "answer_text": a.answer_text if a else None,
                "confidence": a.confidence if a else None,
                "needs_review": a.needs_review if a else None,
                "evaluator_verdict": a.evaluator_verdict if a else None,
            })
        vendors.append({
            "rfx_vendor_id": rv.id,
            "vendor_id": rv.vendor_id,
            "name": vendor_by_id[rv.vendor_id].name,
            "answers": answers,
        })
    return {"vendors": vendors}


def price_rankings(comparison: dict) -> list[dict]:
    """Per line item, vendors ranked by normalized price ascending - computed
    once in Python so the analyst agent never has to compare N prices itself."""
    rankings = []
    for row in comparison["rows"]:
        candidates = []
        for vendor in comparison["vendors"]:
            cell = row["cells"].get(str(vendor["rfx_vendor_id"]))
            if cell and cell["unit_price_normalized"] is not None:
                candidates.append({
                    "vendor_id": vendor["vendor_id"],
                    "vendor_name": vendor["name"],
                    "unit_price_normalized": cell["unit_price_normalized"],
                    "lead_time_days": cell["lead_time_days"],
                    "needs_review": cell["needs_review"],
                    "evaluator_verdict": cell["evaluator_verdict"],
                })
        candidates.sort(key=lambda c: c["unit_price_normalized"])
        rankings.append({
            "sku_code": row["sku_code"],
            "description": row["description"],
            "quantity": row["quantity"],
            "unit": row["unit"],
            "ranked_vendors": candidates,
        })
    return rankings


def rfx_summary(session: Session, rfx_id: int) -> Rfx | None:
    return session.get(Rfx, rfx_id)
