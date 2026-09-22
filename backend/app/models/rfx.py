from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from .enums import QuestionType, RfxStatus, VendorResponseStatus

if TYPE_CHECKING:
    from .vendor import Vendor


class Rfx(SQLModel, table=True):
    __tablename__ = "rfx"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    category: str
    scope_description: str = ""
    status: RfxStatus = Field(default=RfxStatus.DRAFT)
    canonical_currency: str = Field(default="INR")
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    validity_days: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    line_items: List["RfxLineItem"] = Relationship(back_populates="rfx")
    questions: List["RfxQuestion"] = Relationship(back_populates="rfx")
    rfx_vendors: List["RfxVendor"] = Relationship(back_populates="rfx")


class RfxLineItem(SQLModel, table=True):
    __tablename__ = "rfx_line_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfx.id")
    line_no: int
    sku_code: str
    description: str
    # Free-form spec fields (ply, gsm, dimensions_mm, printed, ...). Kept as
    # JSON rather than fixed columns since spec shape varies by category and
    # the category is a build-time choice, not a schema-time one.
    spec_attributes: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    quantity: float
    unit: str
    reference_unit_price: Optional[float] = None
    reference_period_label: Optional[str] = None

    rfx: Optional[Rfx] = Relationship(back_populates="line_items")


class RfxQuestion(SQLModel, table=True):
    __tablename__ = "rfx_question"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfx.id")
    question_no: int
    question_text: str
    question_type: QuestionType = Field(default=QuestionType.TEXT)
    required: bool = Field(default=True)

    rfx: Optional[Rfx] = Relationship(back_populates="questions")


class RfxVendor(SQLModel, table=True):
    """Join between an RFx and an invited vendor, tracking where that
    vendor's response currently stands."""

    __tablename__ = "rfx_vendor"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfx.id")
    vendor_id: int = Field(foreign_key="vendor.id")
    sent_at: Optional[datetime] = None
    response_status: VendorResponseStatus = Field(default=VendorResponseStatus.PENDING)

    rfx: Optional[Rfx] = Relationship(back_populates="rfx_vendors")
    vendor: Optional["Vendor"] = Relationship(back_populates="rfx_vendors")
