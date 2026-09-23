import json
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine, select

from app import models  # noqa: F401 - import registers all tables on SQLModel.metadata
from app.config import get_settings
from app.models import Vendor

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def seed_vendors_if_empty() -> None:
    """Loads the 5 fabricated vendors from the seed dataset into the DB, once.
    Real vendor onboarding is out of scope for v0 - this just gives the "send
    to vendors" action someone real to send to."""
    with Session(engine) as session:
        if session.exec(select(Vendor)).first():
            return
        path = Path(settings.seed_data_dir) / "vendors.json"
        for entry in json.loads(path.read_text(encoding="utf-8")):
            session.add(Vendor(
                name=entry["name"],
                contact_email=entry["contact_email"],
                persona_notes=entry.get("persona_notes"),
            ))
        session.commit()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
