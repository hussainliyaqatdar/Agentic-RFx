from pathlib import Path

from sqlmodel import Session, select

from app.config import get_settings
from app.models import (
    DocumentType,
    ExtractedAnswer,
    ExtractedLineQuote,
    Rfx,
    RfxLineItem,
    RfxQuestion,
    RfxVendor,
    Vendor,
    VendorResponseDocument,
    VendorResponseStatus,
)

from .pipeline import run_pipeline_for_vendor

_DOCUMENT_TYPE_BY_SUFFIX = {
    ".pdf": DocumentType.PDF,
    ".jpg": DocumentType.IMAGE,
    ".jpeg": DocumentType.IMAGE,
    ".png": DocumentType.IMAGE,
    ".xlsx": DocumentType.XLSX,
    ".docx": DocumentType.DOCX,
    ".txt": DocumentType.EMAIL_TEXT,
}


def _ensure_documents(session: Session, rfx_vendor: RfxVendor, vendor_slug: str) -> list[VendorResponseDocument]:
    existing = session.exec(
        select(VendorResponseDocument).where(VendorResponseDocument.rfx_vendor_id == rfx_vendor.id)
    ).all()
    if existing:
        return existing

    vendor_dir = Path(get_settings().seed_data_dir) / "vendors" / vendor_slug
    created = []
    for path in sorted(vendor_dir.iterdir()):
        if path.name.startswith(("~$", ".")):
            continue
        doc_type = _DOCUMENT_TYPE_BY_SUFFIX.get(path.suffix.lower())
        if doc_type is None:
            continue
        doc = VendorResponseDocument(
            rfx_vendor_id=rfx_vendor.id,
            file_name=path.name,
            document_type=doc_type,
            storage_path=f"vendors/{vendor_slug}/{path.name}",
            raw_email_text=path.read_text(encoding="utf-8") if doc_type == DocumentType.EMAIL_TEXT else None,
        )
        session.add(doc)
        created.append(doc)
    session.commit()
    for doc in created:
        session.refresh(doc)
    return created


def _find_citation_document(citation: str | None, documents: list[VendorResponseDocument]) -> VendorResponseDocument:
    if citation:
        for doc in documents:
            if doc.file_name.lower() in citation.lower():
                return doc
    return documents[0]


def run_and_persist_extraction(session: Session, rfx_id: int) -> dict:
    """Runs Module 3's worker->evaluator->merge pipeline for every vendor on
    this Rfx and writes the results as ExtractedLineQuote/ExtractedAnswer rows
    - the first time this pipeline's output has been persisted rather than
    just returned as a dict. Makes real Gemini calls; costs real money."""
    rfx = session.get(Rfx, rfx_id)
    if not rfx:
        raise ValueError(f"Rfx {rfx_id} not found")

    line_item_by_sku = {
        li.sku_code: li for li in session.exec(select(RfxLineItem).where(RfxLineItem.rfx_id == rfx_id)).all()
    }
    question_by_no = {
        q.question_no: q for q in session.exec(select(RfxQuestion).where(RfxQuestion.rfx_id == rfx_id)).all()
    }

    rfx_vendors = session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx_id)).all()
    summary = []
    for rfx_vendor in rfx_vendors:
        vendor = session.get(Vendor, rfx_vendor.vendor_id)
        if not vendor or not vendor.slug:
            continue

        # Clear any prior extraction for this vendor so re-running is idempotent.
        for line in session.exec(
            select(ExtractedLineQuote).where(ExtractedLineQuote.rfx_vendor_id == rfx_vendor.id)
        ).all():
            session.delete(line)
        for ans in session.exec(
            select(ExtractedAnswer).where(ExtractedAnswer.rfx_vendor_id == rfx_vendor.id)
        ).all():
            session.delete(ans)
        rfx_vendor.response_status = VendorResponseStatus.EXTRACTING
        session.add(rfx_vendor)
        session.commit()

        try:
            documents = _ensure_documents(session, rfx_vendor, vendor.slug)
            output = run_pipeline_for_vendor(vendor.slug)
        except Exception:
            rfx_vendor.response_status = VendorResponseStatus.ERROR
            session.add(rfx_vendor)
            session.commit()
            raise

        line_count = 0
        for line in output["lines"]:
            rfx_line_item = line_item_by_sku.get(line["sku_code"]) if line["sku_code"] else None
            doc = _find_citation_document(line.get("source_citation"), documents)
            session.add(ExtractedLineQuote(
                rfx_vendor_id=rfx_vendor.id,
                source_document_id=doc.id,
                rfx_line_item_id=rfx_line_item.id if rfx_line_item else None,
                vendor_raw_description=line.get("vendor_raw_description") or "",
                match_confidence=line.get("match_confidence"),
                quantity_quoted=line.get("quantity_quoted"),
                unit_quoted=line.get("unit_quoted"),
                unit_price_quoted=line.get("unit_price_quoted"),
                currency_quoted=line.get("currency_quoted"),
                unit_price_normalized=line.get("unit_price_normalized"),
                currency_normalized=line.get("currency_normalized"),
                conversion_notes=line.get("conversion_notes"),
                lead_time_days=line.get("lead_time_days"),
                discount_notes=line.get("discount_notes"),
                extraction_confidence=line.get("extraction_confidence"),
                needs_review=line.get("needs_review", True),
                source_citation=line.get("source_citation"),
                evaluator_verdict=line.get("evaluator_verdict"),
                evaluator_reasoning=line.get("evaluator_reasoning"),
            ))
            line_count += 1

        answer_count = 0
        for ans in output["answers"]:
            rfx_question = question_by_no.get(ans["question_no"])
            if not rfx_question:
                continue
            doc = _find_citation_document(ans.get("source_citation"), documents)
            session.add(ExtractedAnswer(
                rfx_vendor_id=rfx_vendor.id,
                rfx_question_id=rfx_question.id,
                source_document_id=doc.id,
                answer_text=ans.get("answer_text"),
                confidence=ans.get("confidence"),
                source_citation=ans.get("source_citation"),
                needs_review=ans.get("needs_review", False),
                evaluator_verdict=ans.get("evaluator_verdict"),
                evaluator_reasoning=ans.get("evaluator_reasoning"),
            ))
            answer_count += 1

        rfx_vendor.response_status = VendorResponseStatus.EXTRACTED
        session.add(rfx_vendor)
        session.commit()
        summary.append({"vendor": vendor.name, "lines": line_count, "answers": answer_count})

    return {"vendors_processed": len(summary), "detail": summary}
