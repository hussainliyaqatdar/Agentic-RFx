from pathlib import Path
from typing import Optional

from app.models._timestamps import utcnow

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import (
    AwardLineItem,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatSessionType,
    ExtractedAnswer,
    ExtractedLineQuote,
    QuestionType,
    Rfx,
    RfxLineItem,
    RfxQuestion,
    RfxStatus,
    RfxVendor,
    Vendor,
    VendorResponseDocument,
    VendorResponseStatus,
)
from app.services.analyst.agent import run_analyst_turn
from app.services.analyst.context import format_analyst_context
from app.services.comparison import build_comparison_data, build_questionnaire_data
from app.services.copilot.agent import run_copilot_turn
from app.services.copilot.schemas import RfxDraft
from app.services.extraction.persistence import run_and_persist_extraction

router = APIRouter(tags=["rfx"])


@router.get("/rfx")
def list_rfx(session: Session = Depends(get_session)):
    rows = session.exec(select(Rfx).order_by(Rfx.created_at.desc())).all()
    result = []
    for rfx in rows:
        line_items = session.exec(select(RfxLineItem).where(RfxLineItem.rfx_id == rfx.id)).all()
        rfx_vendors = session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx.id)).all()
        result.append({
            "id": rfx.id,
            "title": rfx.title,
            "category": rfx.category,
            "status": rfx.status,
            "line_item_count": len(line_items),
            "vendor_count": len(rfx_vendors),
            "created_at": rfx.created_at,
        })
    return result


@router.get("/rfx/{rfx_id}")
def get_rfx(rfx_id: int, session: Session = Depends(get_session)):
    rfx = session.get(Rfx, rfx_id)
    if not rfx:
        raise HTTPException(status_code=404, detail="RFx not found")
    line_items = session.exec(
        select(RfxLineItem).where(RfxLineItem.rfx_id == rfx_id).order_by(RfxLineItem.line_no)
    ).all()
    questions = session.exec(
        select(RfxQuestion).where(RfxQuestion.rfx_id == rfx_id).order_by(RfxQuestion.question_no)
    ).all()
    rfx_vendors = session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx_id)).all()
    vendors_by_id = {}
    if rfx_vendors:
        vendor_ids = [rv.vendor_id for rv in rfx_vendors]
        for v in session.exec(select(Vendor).where(Vendor.id.in_(vendor_ids))).all():
            vendors_by_id[v.id] = v

    return {
        "id": rfx.id,
        "title": rfx.title,
        "category": rfx.category,
        "scope_description": rfx.scope_description,
        "status": rfx.status,
        "canonical_currency": rfx.canonical_currency,
        "payment_terms": rfx.payment_terms,
        "delivery_terms": rfx.delivery_terms,
        "validity_days": rfx.validity_days,
        "created_at": rfx.created_at,
        "line_items": [li.model_dump() for li in line_items],
        "questions": [q.model_dump() for q in questions],
        "vendors": [
            {"id": rv.vendor_id, "name": vendors_by_id[rv.vendor_id].name,
             "response_status": rv.response_status, "sent_at": rv.sent_at}
            for rv in rfx_vendors if rv.vendor_id in vendors_by_id
        ],
    }


class CopilotTurnRequest(BaseModel):
    session_id: Optional[int] = None
    message: str


@router.post("/copilot/turn")
def copilot_turn(payload: CopilotTurnRequest, session: Session = Depends(get_session)):
    if payload.session_id:
        chat_session = session.get(ChatSession, payload.session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        chat_session = ChatSession(session_type=ChatSessionType.RFX_DRAFTING)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)

    prior = session.exec(
        select(ChatMessage).where(ChatMessage.session_id == chat_session.id).order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": m.role.value, "content": m.content} for m in prior]
    current_draft = RfxDraft.model_validate(chat_session.draft_state) if chat_session.draft_state else None

    result = run_copilot_turn(history, current_draft, payload.message, label=f"copilot:{chat_session.id}")

    session.add(ChatMessage(session_id=chat_session.id, role=ChatRole.USER, content=payload.message))
    session.add(ChatMessage(session_id=chat_session.id, role=ChatRole.ASSISTANT, content=result.reply))
    chat_session.draft_state = result.draft.model_dump()
    session.add(chat_session)
    session.commit()

    return {
        "session_id": chat_session.id,
        "reply": result.reply,
        "draft": result.draft.model_dump(),
        "ready_to_finalize": result.ready_to_finalize,
    }


@router.post("/copilot/{session_id}/finalize")
def finalize_draft(session_id: int, session: Session = Depends(get_session)):
    chat_session = session.get(ChatSession, session_id)
    if not chat_session or not chat_session.draft_state:
        raise HTTPException(status_code=400, detail="No draft to finalize for this session")
    draft = RfxDraft.model_validate(chat_session.draft_state)
    if not draft.line_items:
        raise HTTPException(status_code=400, detail="Draft has no line items yet")

    rfx = Rfx(
        title=draft.title or "Untitled RFx",
        category=draft.category or "General",
        scope_description=draft.scope_description or "",
        status=RfxStatus.DRAFT,
        payment_terms=draft.payment_terms,
        delivery_terms=draft.delivery_terms,
        validity_days=draft.validity_days,
    )
    session.add(rfx)
    session.commit()
    session.refresh(rfx)

    for i, li in enumerate(draft.line_items, start=1):
        session.add(RfxLineItem(
            rfx_id=rfx.id,
            line_no=i,
            sku_code=li.sku_code or f"NEW-{rfx.id}-{i:03d}",
            description=li.description,
            spec_attributes={"summary": li.spec_summary} if li.spec_summary else {},
            quantity=li.quantity,
            unit=li.unit,
        ))
    for i, q in enumerate(draft.questions, start=1):
        try:
            q_type = QuestionType(q.question_type)
        except ValueError:
            q_type = QuestionType.TEXT
        session.add(RfxQuestion(
            rfx_id=rfx.id,
            question_no=q.question_no or i,
            question_text=q.question_text,
            question_type=q_type,
        ))

    chat_session.rfx_id = rfx.id
    session.add(chat_session)
    session.commit()

    return {"rfx_id": rfx.id}


@router.post("/rfx/{rfx_id}/send")
def send_rfx(rfx_id: int, session: Session = Depends(get_session)):
    rfx = session.get(Rfx, rfx_id)
    if not rfx:
        raise HTTPException(status_code=404, detail="RFx not found")

    vendors = session.exec(select(Vendor)).all()
    if not vendors:
        raise HTTPException(status_code=503, detail="No vendors seeded yet")

    for v in vendors:
        existing = session.exec(
            select(RfxVendor).where(RfxVendor.rfx_id == rfx_id, RfxVendor.vendor_id == v.id)
        ).first()
        if not existing:
            session.add(RfxVendor(
                rfx_id=rfx_id, vendor_id=v.id, sent_at=utcnow(),
                response_status=VendorResponseStatus.PENDING,
            ))

    rfx.status = RfxStatus.SENT
    session.add(rfx)
    session.commit()

    return {"status": "sent", "vendor_count": len(vendors)}


@router.post("/rfx/{rfx_id}/extract")
def extract_rfx(rfx_id: int, session: Session = Depends(get_session)):
    """Runs Module 3 for real against every vendor on this RFx and persists
    the results. Makes real Gemini calls - not instant, not free."""
    rfx = session.get(Rfx, rfx_id)
    if not rfx:
        raise HTTPException(status_code=404, detail="RFx not found")
    try:
        result = run_and_persist_extraction(session, rfx_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # All vendors have responded and been processed - move the RFx from
    # "sent" to "responded" so the buyer knows there's something to review.
    rfx_vendors = session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx_id)).all()
    if rfx_vendors and all(rv.response_status == VendorResponseStatus.EXTRACTED for rv in rfx_vendors):
        rfx.status = RfxStatus.RESPONSES_IN
        session.add(rfx)
        session.commit()

    return result


@router.get("/rfx/{rfx_id}/comparison")
def get_comparison(rfx_id: int, session: Session = Depends(get_session)):
    if not session.get(Rfx, rfx_id):
        raise HTTPException(status_code=404, detail="RFx not found")
    return build_comparison_data(session, rfx_id)


@router.get("/rfx/{rfx_id}/vendors/{vendor_id}/detail")
def get_vendor_detail(rfx_id: int, vendor_id: int, session: Session = Depends(get_session)):
    rfx_vendor = session.exec(
        select(RfxVendor).where(RfxVendor.rfx_id == rfx_id, RfxVendor.vendor_id == vendor_id)
    ).first()
    if not rfx_vendor:
        raise HTTPException(status_code=404, detail="Vendor not attached to this RFx")
    vendor = session.get(Vendor, vendor_id)

    questions = session.exec(
        select(RfxQuestion).where(RfxQuestion.rfx_id == rfx_id).order_by(RfxQuestion.question_no)
    ).all()
    answers_by_question = {
        a.rfx_question_id: a
        for a in session.exec(select(ExtractedAnswer).where(ExtractedAnswer.rfx_vendor_id == rfx_vendor.id)).all()
    }
    documents = session.exec(
        select(VendorResponseDocument).where(VendorResponseDocument.rfx_vendor_id == rfx_vendor.id)
    ).all()

    return {
        "vendor": {"id": vendor.id, "name": vendor.name, "contact_email": vendor.contact_email},
        "response_status": rfx_vendor.response_status,
        "answers": [
            {
                "question_no": q.question_no,
                "question_text": q.question_text,
                "answer_text": answers_by_question[q.id].answer_text if q.id in answers_by_question else None,
                "confidence": answers_by_question[q.id].confidence if q.id in answers_by_question else None,
                "needs_review": answers_by_question[q.id].needs_review if q.id in answers_by_question else None,
                "evaluator_verdict": answers_by_question[q.id].evaluator_verdict if q.id in answers_by_question else None,
            }
            for q in questions
        ],
        "documents": [
            {"id": d.id, "file_name": d.file_name, "document_type": d.document_type} for d in documents
        ],
    }


@router.get("/rfx/{rfx_id}/documents/{document_id}/download")
def download_document(rfx_id: int, document_id: int, session: Session = Depends(get_session)):
    doc = session.get(VendorResponseDocument, document_id)
    if not doc or not doc.storage_path:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = Path(get_settings().seed_data_dir) / doc.storage_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path=file_path, filename=doc.file_name)


class AnalystTurnRequest(BaseModel):
    session_id: Optional[int] = None
    message: str


@router.post("/rfx/{rfx_id}/analyst/turn")
def analyst_turn(rfx_id: int, payload: AnalystTurnRequest, session: Session = Depends(get_session)):
    rfx = session.get(Rfx, rfx_id)
    if not rfx:
        raise HTTPException(status_code=404, detail="RFx not found")

    if payload.session_id:
        chat_session = session.get(ChatSession, payload.session_id)
        if not chat_session or chat_session.rfx_id != rfx_id:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        chat_session = ChatSession(session_type=ChatSessionType.ANALYST, rfx_id=rfx_id)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)

    prior = session.exec(
        select(ChatMessage).where(ChatMessage.session_id == chat_session.id).order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": m.role.value, "content": m.content} for m in prior]

    comparison = build_comparison_data(session, rfx_id)
    questionnaire = build_questionnaire_data(session, rfx_id)
    reference_context = format_analyst_context(rfx, comparison, questionnaire)

    result = run_analyst_turn(reference_context, history, payload.message, label=f"analyst:{chat_session.id}")

    session.add(ChatMessage(session_id=chat_session.id, role=ChatRole.USER, content=payload.message))
    session.add(ChatMessage(session_id=chat_session.id, role=ChatRole.ASSISTANT, content=result.reply))
    session.commit()

    # The exact total for any proposed award is computed here, in plain code,
    # from the real persisted quotes - never asserted by the model itself.
    computed_total = None
    if result.proposed_award:
        line_by_sku = {
            li.sku_code: li for li in session.exec(select(RfxLineItem).where(RfxLineItem.rfx_id == rfx_id)).all()
        }
        rfx_vendor_by_vendor_id = {
            rv.vendor_id: rv for rv in session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx_id)).all()
        }
        total = 0.0
        priced_lines = 0
        vendor_ids_used: set[int] = set()
        unpriceable: list[str] = []
        for line in result.proposed_award:
            li = line_by_sku.get(line.sku_code)
            rv = rfx_vendor_by_vendor_id.get(line.vendor_id)
            quote = None
            if li and rv:
                quote = session.exec(
                    select(ExtractedLineQuote).where(
                        ExtractedLineQuote.rfx_vendor_id == rv.id, ExtractedLineQuote.rfx_line_item_id == li.id
                    )
                ).first()
            if not li or not rv or not quote or quote.unit_price_normalized is None:
                unpriceable.append(line.sku_code)
                continue
            total += quote.unit_price_normalized * li.quantity
            priced_lines += 1
            vendor_ids_used.add(line.vendor_id)
        computed_total = {
            "total_amount": round(total, 2),
            "currency": rfx.canonical_currency,
            "line_count": priced_lines,
            "vendor_count": len(vendor_ids_used),
            "unpriceable_skus": unpriceable,
        }

    return {
        "session_id": chat_session.id,
        "reply": result.reply,
        "proposed_award": [pa.model_dump() for pa in result.proposed_award],
        "confidence_note": result.confidence_note,
        "computed_total": computed_total,
    }


class AwardRequest(BaseModel):
    awards: dict[str, int]  # sku_code -> vendor_id


@router.post("/rfx/{rfx_id}/award")
def award_rfx(rfx_id: int, payload: AwardRequest, session: Session = Depends(get_session)):
    rfx = session.get(Rfx, rfx_id)
    if not rfx:
        raise HTTPException(status_code=404, detail="RFx not found")

    line_items = session.exec(select(RfxLineItem).where(RfxLineItem.rfx_id == rfx_id)).all()
    if len(payload.awards) < len(line_items):
        raise HTTPException(
            status_code=400,
            detail=f"Award must cover all {len(line_items)} line items ({len(payload.awards)} given)",
        )

    rfx_vendors = session.exec(select(RfxVendor).where(RfxVendor.rfx_id == rfx_id)).all()
    rfx_vendor_by_vendor_id = {rv.vendor_id: rv for rv in rfx_vendors}

    # Clear any prior award for this RFx so re-committing replaces, not duplicates.
    existing_awards = session.exec(
        select(AwardLineItem).where(AwardLineItem.rfx_line_item_id.in_([li.id for li in line_items]))
    ).all()
    for existing in existing_awards:
        session.delete(existing)
    session.commit()

    for li in line_items:
        vendor_id = payload.awards.get(li.sku_code)
        if vendor_id is None:
            raise HTTPException(status_code=400, detail=f"No vendor assigned for {li.sku_code}")
        rv = rfx_vendor_by_vendor_id.get(vendor_id)
        if not rv:
            raise HTTPException(status_code=400, detail=f"Vendor {vendor_id} is not attached to this RFx")
        quote = session.exec(
            select(ExtractedLineQuote).where(
                ExtractedLineQuote.rfx_vendor_id == rv.id, ExtractedLineQuote.rfx_line_item_id == li.id
            )
        ).first()
        if not quote or quote.unit_price_normalized is None:
            raise HTTPException(status_code=400, detail=f"No priced quote from vendor {vendor_id} for {li.sku_code}")
        session.add(AwardLineItem(
            rfx_line_item_id=li.id,
            awarded_vendor_id=vendor_id,
            awarded_unit_price=quote.unit_price_normalized,
            awarded_currency=quote.currency_normalized or rfx.canonical_currency,
        ))

    rfx.status = RfxStatus.AWARDED
    session.add(rfx)
    session.commit()

    return {"status": "awarded", "line_items_awarded": len(line_items)}
