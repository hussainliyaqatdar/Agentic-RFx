from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from ._timestamps import utcnow
from .enums import DocumentType


class VendorResponseDocument(SQLModel, table=True):
    """A raw file (or raw email body) as a vendor actually sent it -
    whatever shape it arrived in. Extraction always reads from here, never
    from a pre-normalized copy, so the pipeline stays honest about what it
    was actually given."""

    __tablename__ = "vendor_response_document"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_vendor_id: int = Field(foreign_key="rfx_vendor.id")
    file_name: str
    document_type: DocumentType
    storage_path: Optional[str] = None
    raw_email_text: Optional[str] = None
    received_at: datetime = Field(default_factory=utcnow)
