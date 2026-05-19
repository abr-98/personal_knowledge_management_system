from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.domain.entities import ChatMessage, ChatThread, Record, TimelineEvent, User, WorkItem


class AuthRepository(Protocol):
    def create_user(self, email: str, password_hash: str, plan_type: str = "free") -> User: ...
    def get_user_by_email(self, email: str) -> User | None: ...
    def get_user_by_id(self, user_id: int) -> User | None: ...
    def update_password(self, user_id: int, password_hash: str) -> User | None: ...


class ChatRepository(Protocol):
    def create_thread(self, user_id: int, title: str) -> ChatThread: ...
    def list_threads(self, user_id: int) -> list[ChatThread]: ...
    def get_thread(self, user_id: int, thread_id: int) -> ChatThread | None: ...
    def update_thread(self, user_id: int, thread_id: int, title: str) -> ChatThread | None: ...
    def delete_thread(self, user_id: int, thread_id: int) -> bool: ...
    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        token_count: int = 0,
        model: str = "gpt-4.1-mini",
    ) -> ChatMessage: ...
    def list_messages(self, thread_id: int) -> list[ChatMessage]: ...
    def record_token_usage(
        self,
        user_id: int,
        thread_id: int | None,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        model: str,
        cost: float,
        timestamp: datetime | None = None,
    ) -> None: ...


class RecordRepository(Protocol):
    def create_record(
        self,
        user_id: str,
        link_or_path: str,
        domain: str,
        source: str | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> Record: ...
    def list_records(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        domain: str | None = None,
    ) -> list[Record]: ...
    def get_record(self, user_id: str, record_id: int) -> Record | None: ...
    def update_record(
        self,
        user_id: str,
        record_id: int,
        link_or_path: str | None = None,
        source: str | None = None,
        domain: str | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> Record | None: ...
    def delete_record(self, user_id: str, record_id: int) -> bool: ...
    def fetch_user_records(self, user_id: str) -> list[dict[str, object]]: ...
    def update_tags(self, record_id: int, user_id: str, new_tags: list[str]) -> bool: ...
    def update_topics(self, record_id: int, user_id: str, new_topics: list[str]) -> bool: ...
    def get_records_by_tags(self, user_id: str, tags: list[str]) -> list[dict[str, object]]: ...
    def search_records(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        domain: str | None = None,
    ) -> list[dict[str, object]]: ...


class UserNotesRepository(Protocol):
    def insert_note(
        self,
        user_id: str,
        md_file_path: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> int: ...
    def search_notes(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, object]]: ...
    def retrieve_notes(self, user_id: str, query: str) -> list[dict[str, object]]: ...
    def build_notes_graph(self, user_id: str) -> dict[str, list[dict[str, object]]]: ...


class WorkItemRepository(Protocol):
    def create_workitem(
        self,
        user_id: str,
        title: str,
        description: str | None = None,
        status: str = "pending",
        priority: str = "medium",
        related_notes: list[str] | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        due_date: datetime | None = None,
    ) -> WorkItem: ...
    def list_workitems(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[WorkItem]: ...
    def get_workitem(self, user_id: str, workitem_id: int) -> WorkItem | None: ...
    def update_workitem(
        self,
        user_id: str,
        workitem_id: int,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        related_notes: list[str] | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        due_date: datetime | None = None,
    ) -> WorkItem | None: ...
    def delete_workitem(self, user_id: str, workitem_id: int) -> bool: ...


class TimelineRepository(Protocol):
    def create_timeline_event(
        self,
        user_id: str,
        event_type: str,
        title: str,
        description: str | None = None,
        related_notes: list[str] | None = None,
        related_workitems: list[int] | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> TimelineEvent: ...
    def list_timeline_events(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[TimelineEvent]: ...
    def get_timeline_event(self, user_id: str, event_id: int) -> TimelineEvent | None: ...
    def update_timeline_event(
        self,
        user_id: str,
        event_id: int,
        event_type: str | None = None,
        title: str | None = None,
        description: str | None = None,
        related_notes: list[str] | None = None,
        related_workitems: list[int] | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> TimelineEvent | None: ...
    def delete_timeline_event(self, user_id: str, event_id: int) -> bool: ...