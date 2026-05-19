from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class WorkItemStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class WorkItemPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChatRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(slots=True)
class User:
    id: int
    email: str
    password_hash: str
    created_at: datetime
    plan_type: str = "free"
    token_usage: int = 0


@dataclass(slots=True)
class ChatThread:
    id: int
    user_id: int
    title: str
    created_at: datetime


@dataclass(slots=True)
class ChatMessage:
    id: int
    thread_id: int
    role: ChatRole | str
    content: str
    token_count: int
    model: str
    created_at: datetime


@dataclass(slots=True)
class Record:
    id: int
    user_id: str
    link_or_path: str
    created_at: datetime
    domain: str
    source: str | None = None
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkItem:
    id: int
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    status: WorkItemStatus | str = WorkItemStatus.PENDING
    priority: WorkItemPriority | str = WorkItemPriority.MEDIUM
    related_notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    due_date: datetime | None = None


@dataclass(slots=True)
class TimelineEvent:
    id: int
    user_id: str
    created_at: datetime
    event_type: str | None = None
    title: str | None = None
    description: str | None = None
    related_notes: list[str] = field(default_factory=list)
    related_workitems: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)