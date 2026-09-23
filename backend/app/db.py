import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine, select

from app import models  # noqa: F401 - import registers all tables on SQLModel.metadata
from app.config import get_settings
from app.models import (
    QuestionType,
    Rfx,
    RfxLineItem,
    RfxQuestion,
    RfxStatus,
    RfxVendor,
    Vendor,
    VendorResponseStatus,
)

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def _seed_dir() -> Path:
    return Path(settings.seed_data_dir)


def seed_vendors_if_empty() -> None:
    """Loads the 5 fabricated vendors from the seed dataset into the DB, once.
    Real vendor onboarding is out of scope for v0 - this just gives the "send
    to vendors" action someone real to send to."""
    with Session(engine) as session:
        if session.exec(select(Vendor)).first():
            return
        path = _seed_dir() / "vendors.json"
        for entry in json.loads(path.read_text(encoding="utf-8")):
            session.add(Vendor(
                name=entry["name"],
                contact_email=entry["contact_email"],
                slug=entry["slug"],
                persona_notes=entry.get("persona_notes"),
            ))
        session.commit()


def seed_demo_rfx_if_missing() -> None:
    """Creates the full 30-line-item YoloMart RFx from the seed dataset and
    marks it as sent to all 5 vendors, so there's a real, reproducible RFx for
    the comparison view to run extraction against - without replaying the
    co-pilot conversation (and its Gemini cost) just to reconstruct demo data."""
    with Session(engine) as session:
        rfx_meta = json.loads((_seed_dir() / "rfx.json").read_text(encoding="utf-8"))
        existing = session.exec(select(Rfx).where(Rfx.title == rfx_meta["title"])).first()
        if existing:
            return

        rfx = Rfx(
            title=rfx_meta["title"],
            category=rfx_meta["category"],
            scope_description=rfx_meta["scope_description"],
            status=RfxStatus.SENT,
            canonical_currency=rfx_meta["canonical_currency"],
            payment_terms=rfx_meta["payment_terms"],
            delivery_terms=rfx_meta["delivery_terms"],
            validity_days=rfx_meta["validity_days"],
        )
        session.add(rfx)
        session.commit()
        session.refresh(rfx)

        line_items = json.loads((_seed_dir() / "line_items.json").read_text(encoding="utf-8"))
        for li in line_items:
            session.add(RfxLineItem(
                rfx_id=rfx.id,
                line_no=li["line_no"],
                sku_code=li["sku_code"],
                description=li["description"],
                spec_attributes=li["spec_attributes"],
                quantity=li["quantity"],
                unit=li["unit"],
                reference_unit_price=li["reference_unit_price"],
                reference_period_label=li["reference_period_label"],
            ))

        questions = json.loads((_seed_dir() / "questionnaire.json").read_text(encoding="utf-8"))
        for q in questions:
            session.add(RfxQuestion(
                rfx_id=rfx.id,
                question_no=q["question_no"],
                question_text=q["question_text"],
                question_type=QuestionType(q["question_type"]),
            ))

        sent_at = datetime.now(timezone.utc)
        for vendor in session.exec(select(Vendor)).all():
            session.add(RfxVendor(
                rfx_id=rfx.id, vendor_id=vendor.id, sent_at=sent_at,
                response_status=VendorResponseStatus.PENDING,
            ))

        session.commit()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
