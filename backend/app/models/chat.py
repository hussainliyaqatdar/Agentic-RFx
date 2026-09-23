from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import JSON, Column, Field, SQLModel

from ._timestamps import utcnow
from .enums import ChatRole, ChatSessionType


class ChatSession(SQLModel, table=True):
    """Covers both the RFx-drafting co-pilot and the post-award analyst
    conversation - same shape, different session_type, so the two agent
    loops don't need parallel history tables."""

    __tablename__ = "chat_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Null while an RFX_DRAFTING session is still in progress - there's no Rfx
    # row yet until the buyer finalizes the draft. Always set for ANALYST
    # sessions, which only start once an Rfx (and its vendor responses) exist.
    rfx_id: Optional[int] = Field(default=None, foreign_key="rfx.id")
    session_type: ChatSessionType
    # The in-progress RFx draft (title/category/line items/questions/terms) as
    # the co-pilot last left it. Round-tripped every turn instead of asking the
    # frontend to resend full state, and written into real Rfx/RfxLineItem/
    # RfxQuestion rows only when the buyer finalizes.
    draft_state: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_session.id")
    role: ChatRole
    content: str
    # Tool calls/results for this turn, kept for transparency - the
    # analyst chat's answers should be traceable back to the query it ran.
    tool_calls: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    attachments: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
