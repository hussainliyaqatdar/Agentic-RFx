from typing import Optional

from pydantic import BaseModel, Field


class DraftLineItem(BaseModel):
    sku_code: Optional[str] = Field(None, description="Existing canonical SKU code if this matches the catalog below - null if it's a genuinely new item")
    is_new_sku: bool = Field(description="True if no canonical item fits and this would be a new catalog entry")
    description: str
    spec_summary: str = Field(default="", description="Short human-readable spec, e.g. '3-ply, B-flute, 300x200x150mm, plain kraft' - not a structured object")
    quantity: float
    unit: str


class DraftQuestion(BaseModel):
    question_no: Optional[int] = Field(None, description="Existing questionnaire question number if reused from the catalog below - null if newly written for this RFx")
    question_text: str
    question_type: str


class RfxDraft(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    scope_description: Optional[str] = None
    line_items: list[DraftLineItem] = Field(default_factory=list)
    questions: list[DraftQuestion] = Field(default_factory=list)
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    validity_days: Optional[int] = None


class CopilotTurnOutput(BaseModel):
    reply: str = Field(description="Conversational reply to show the buyer - confirm what changed, ask a clarifying question, or summarize the draft so far")
    draft: RfxDraft
    ready_to_finalize: bool = Field(description="True only once the draft has at least one line item and enough terms to be worth the buyer reviewing")
