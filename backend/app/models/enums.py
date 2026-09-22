from enum import Enum


class RfxStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    SENT = "sent"
    RESPONSES_IN = "responses_in"
    AWARDED = "awarded"
    CLOSED = "closed"


class VendorResponseStatus(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    EXTRACTED = "extracted"
    ERROR = "error"


class DocumentType(str, Enum):
    XLSX = "xlsx"
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    EMAIL_TEXT = "email_text"


class QuestionType(str, Enum):
    YES_NO = "yes_no"
    TEXT = "text"
    CHOICE = "choice"
    NUMBER = "number"


class ChatSessionType(str, Enum):
    RFX_DRAFTING = "rfx_drafting"
    ANALYST = "analyst"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
