from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from ._timestamps import utcnow


class ExtractedLineQuote(SQLModel, table=True):
    """One vendor's quoted price for one (matched) line item, as read
    straight off their document plus the normalization applied on top.

    match_confidence and extraction_confidence are tracked separately on
    purpose: a wrong-SKU match and a misread number are different failure
    modes and the buyer needs to know which one they're looking at.
    """

    __tablename__ = "extracted_line_quote"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_vendor_id: int = Field(foreign_key="rfx_vendor.id")
    source_document_id: int = Field(foreign_key="vendor_response_document.id")
    # Null when the vendor's line couldn't be confidently matched to any
    # canonical line item - surfaced to the buyer as unmatched, not dropped.
    rfx_line_item_id: Optional[int] = Field(default=None, foreign_key="rfx_line_item.id")

    vendor_raw_description: str
    match_confidence: Optional[float] = None

    quantity_quoted: Optional[float] = None
    unit_quoted: Optional[str] = None
    unit_price_quoted: Optional[float] = None
    currency_quoted: Optional[str] = None

    # Normalized to the RFx's canonical unit/currency. conversion_notes
    # records what was assumed (e.g. "1 box = 100 pieces, per vendor spec
    # sheet") so the assumption is inspectable, not just applied silently.
    unit_price_normalized: Optional[float] = None
    currency_normalized: Optional[str] = None
    conversion_notes: Optional[str] = None

    lead_time_days: Optional[int] = None
    discount_notes: Optional[str] = None

    extraction_confidence: Optional[float] = None
    needs_review: bool = Field(default=False)
    # Where in the source document this came from (page/cell/paragraph +
    # quoted snippet), so the buyer can jump from a number to its evidence.
    source_citation: Optional[str] = None

    # The evaluator agent's independent second opinion on this exact line -
    # CONFIRMED / DISPUTED / UNCERTAIN / NOT_REVIEWED / RECOVERED_BY_EVALUATOR
    # (the last for a line the worker never claimed at all but the evaluator
    # determined was addressable). Kept alongside the line, not just in a log,
    # so a review UI can show the disagreement and why in one place.
    evaluator_verdict: Optional[str] = None
    evaluator_reasoning: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)


class ExtractedAnswer(SQLModel, table=True):
    __tablename__ = "extracted_answer"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_vendor_id: int = Field(foreign_key="rfx_vendor.id")
    rfx_question_id: int = Field(foreign_key="rfx_question.id")
    source_document_id: Optional[int] = Field(default=None, foreign_key="vendor_response_document.id")

    answer_text: Optional[str] = None
    answer_bool: Optional[bool] = None
    confidence: Optional[float] = None
    source_citation: Optional[str] = None
    needs_review: bool = Field(default=False)
    evaluator_verdict: Optional[str] = None
    evaluator_reasoning: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)
