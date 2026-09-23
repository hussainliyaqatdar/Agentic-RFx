from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from ._timestamps import utcnow


class AwardLineItem(SQLModel, table=True):
    """The committed award decision, one row per line item so a single RFx
    can be split across vendors. A single-vendor award is just the case
    where every line item happens to point at the same vendor_id."""

    __tablename__ = "award_line_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_line_item_id: int = Field(foreign_key="rfx_line_item.id", unique=True)
    awarded_vendor_id: int = Field(foreign_key="vendor.id")
    awarded_unit_price: float
    awarded_currency: str = Field(default="INR")
    # Short justification, e.g. drawn from the analyst chat's own reasoning,
    # kept alongside the decision for audit/defensibility.
    rationale: Optional[str] = None
    awarded_at: datetime = Field(default_factory=utcnow)
