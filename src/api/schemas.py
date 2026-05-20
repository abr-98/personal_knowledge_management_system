from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.domain.entities import ChatRole, WorkItemPriority, WorkItemStatus


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
    plan_type: str
    token_usage: int


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    plan_type: str = "free"


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ChatThreadCreateRequest(BaseModel):
    user_id: int
    title: str = Field(min_length=1)


class ChatThreadUpdateRequest(BaseModel):
    title: str = Field(min_length=1)


class ChatThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime


class ChatMessageCreateRequest(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1)
    token_count: int = 0
    model: str = "gpt-4.1-mini"


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    role: ChatRole | str
    content: str
    token_count: int
    model: str
    created_at: datetime


class TokenUsageRequest(BaseModel):
    user_id: int
    thread_id: int | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str
    cost: float = 0
    timestamp: datetime | None = None


class RecordUploadRequest(BaseModel):
    user_id: str = Field(min_length=1)
    link: str | None = None
    path: str | None = None
    domain: str | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    record_type: str | None = None  # For file uploads


class RecordUpdateRequest(BaseModel):
    tags: list[str] | None = None
    topics: list[str] | None = None


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    link_or_path: str
    source: str | None = None
    domain: str
    tags: list[str]
    topics: list[str]
    created_at: datetime


class WorkItemCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    related_notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    due_date: datetime | None = None


class WorkItemUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    related_notes: list[str] | None = None
    tags: list[str] | None = None
    topics: list[str] | None = None
    due_date: datetime | None = None


class WorkItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    title: str
    description: str | None = None
    status: WorkItemStatus | str
    priority: WorkItemPriority | str
    related_notes: list[str]
    tags: list[str]
    topics: list[str]
    due_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TimelineEventCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    related_notes: list[str] = Field(default_factory=list)
    related_workitems: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class TimelineEventUpdateRequest(BaseModel):
    event_type: str | None = None
    title: str | None = None
    description: str | None = None
    related_notes: list[str] | None = None
    related_workitems: list[int] | None = None
    tags: list[str] | None = None
    topics: list[str] | None = None


class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    event_type: str | None = None
    title: str | None = None
    description: str | None = None
    related_notes: list[str]
    related_workitems: list[int]
    tags: list[str]
    topics: list[str]
    created_at: datetime


class DeleteResponse(BaseModel):
    deleted: bool = True


class WorkItemOptionsResponse(BaseModel):
    statuses: list[str]
    priorities: list[str]


class HealthResponse(BaseModel):
    status: str


class RecordType(str, Enum):
    GENERIC = "generic"
    PAPERS = "papers"
    PDFS = "pdfs"
    SELF_NOTES = "self-notes"
    TRANSCRIPTS = "transcripts"


class RecordUploadResponse(BaseModel):
    file_name: str
    stored_path: str
    record_type: RecordType
    chunk_count: int