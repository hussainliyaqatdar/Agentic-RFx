from typing import Literal, Optional

from pydantic import BaseModel, Field

Verdict = Literal["CONFIRMED", "DISPUTED", "UNCERTAIN"]


class WorkerLineResult(BaseModel):
    sku_code: Optional[str] = Field(None, description="Matched canonical SKU code, or null if this vendor line matches no canonical item")
    vendor_raw_description: str = Field(description="Exactly how the vendor described this item in their document")
    quantity_quoted: Optional[float] = None
    unit_quoted: Optional[str] = None
    unit_price_quoted: Optional[float] = None
    currency_quoted: Optional[str] = None
    unit_price_normalized: Optional[float] = Field(None, description="Price converted to the RFx's canonical unit and currency")
    currency_normalized: Optional[str] = None
    conversion_notes: Optional[str] = Field(None, description="What was assumed or derived during normalization - unit conversion, currency conversion, discount applied, cross-document reconciliation")
    lead_time_days: Optional[int] = None
    discount_notes: Optional[str] = None
    extraction_confidence: float = Field(description="0-1: how sure the values above are read correctly from the source")
    match_confidence: Optional[float] = Field(None, description="0-1: how sure sku_code is the right canonical match; null if sku_code is null")
    source_citation: str = Field(description="Which document, and a short quoted snippet or location (page/cell/paragraph)")


class WorkerAnswerResult(BaseModel):
    question_no: int
    answer_text: str
    confidence: float
    source_citation: str


class WorkerOutput(BaseModel):
    lines: list[WorkerLineResult]
    answers: list[WorkerAnswerResult]


class EvaluatorLineVerdict(BaseModel):
    line_id: int = Field(description="The line_id this verdict refers to, copied from the claimed extraction you were given")
    verdict: Verdict
    reasoning: str = Field(description="One sentence: why confirmed, what's wrong, or what couldn't be verified")
    suggested_correction: Optional[str] = Field(None, description="The value you believe is correct, if DISPUTED and determinable")


class EvaluatorAnswerVerdict(BaseModel):
    question_no: int
    verdict: Verdict
    reasoning: str


class EvaluatorCoverageGap(BaseModel):
    """A canonical SKU the worker never claimed at all, that the evaluator believes
    the documents actually contain enough information to price - e.g. a blanket
    rate or policy statement that applies to it but was never expanded out."""

    sku_code: str
    reasoning: str = Field(description="Why this SKU is addressable from the documents even though the worker didn't claim it")
    suggested_unit_price_normalized: Optional[float] = Field(None, description="Your best-effort price for this SKU in the RFx's canonical unit/currency, if you can determine one")
    suggested_conversion_notes: Optional[str] = None
    source_citation: str


class EvaluatorOutput(BaseModel):
    line_verdicts: list[EvaluatorLineVerdict]
    answer_verdicts: list[EvaluatorAnswerVerdict]
    coverage_gaps: list[EvaluatorCoverageGap] = Field(
        default_factory=list,
        description="Canonical SKUs the worker didn't claim at all, but that you believe are addressable from the documents",
    )
    overall_notes: Optional[str] = Field(None, description="Anything systemic worth flagging - e.g. a pattern of errors, a document that was hard to read")
