from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import JSON, Column, Field, SQLModel

from .enums import ChatRole, ChatSessionType


class ChatSession(SQLModel, table=True):
    """Covers both the RFx-drafting co-pilot and the post-award analyst
    conversation - same shape, different session_type, so the two agent
    loops don't need parallel history tables."""

    __tablename__ = "chat_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfx_id: int = Field(foreign_key="rfx.id")
    session_type: ChatSessionType
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
