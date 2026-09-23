from typing import Optional

from app.models._timestamps import utcnow

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatSessionType,
    QuestionType,
    Rfx,
    RfxLineItem,
    RfxQuestion,
    RfxStatus,
    RfxVendor,
    Vendor,
    VendorResponseStatus,
)
from app.services.copilot.agent import run_copilot_turn
from app.services.copilot.schemas import RfxDraft

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
