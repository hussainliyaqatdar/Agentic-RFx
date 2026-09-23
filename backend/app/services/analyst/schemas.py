from typing import Optional

from pydantic import BaseModel, Field


class ProposedAwardLine(BaseModel):
    sku_code: str
    vendor_id: int
    vendor_name: str
    reason: str = Field(description="Why this vendor for this line - price, delivery, or compliance, concretely")


class AnalystTurnOutput(BaseModel):
    reply: str = Field(description="Natural-language answer. If the data doesn't support an answer, say so explicitly rather than guessing.")
    proposed_award: list[ProposedAwardLine] = Field(
        default_factory=list,
        description="Only populated when the buyer asked for an award recommendation and there's enough data to propose one - one entry per line item being recommended. Leave empty for questions that aren't asking for a recommendation.",
    )
    confidence_note: Optional[str] = Field(
        None, description="One sentence flagging anything low-confidence, evaluator-disputed, or missing that materially affects this specific answer - null if nothing relevant applies"
    )
