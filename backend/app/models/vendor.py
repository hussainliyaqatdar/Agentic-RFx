from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from ._timestamps import utcnow

if TYPE_CHECKING:
    from .rfx import RfxVendor


class Vendor(SQLModel, table=True):
    __tablename__ = "vendor"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    contact_email: str
    # Internal note on the fabricated persona this vendor plays in the demo
    # dataset (e.g. "quotes in USD", "only covers 27/30 lines"). Not shown
    # to the buyer — it's context for whoever is maintaining the seed data.
    persona_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    rfx_vendors: List["RfxVendor"] = Relationship(back_populates="vendor")


class HistoricalPrice(SQLModel, table=True):
    """Last-period pricing per SKU, used to resolve vendor replies like
    'rest same as last year' during extraction/normalization."""

    __tablename__ = "historical_price"

    id: Optional[int] = Field(default=None, primary_key=True)
    sku_code: str
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id")
    unit_price: float
    currency: str = Field(default="INR")
    unit: str
    period_label: str
