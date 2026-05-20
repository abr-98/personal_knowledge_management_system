from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime
from pathlib import Path

from src.domain.entities import ChatMessage, ChatThread, Record, TimelineEvent, User, WorkItem
from src.domain.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from src.domain.repositories import (
    AuthRepository,
    ChatRepository,
    RecordRepository,
    TimelineRepository,
    UserNotesRepository,
    WorkItemRepository,
)


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    salt_b64, digest_b64 = stored_hash.split("$", 1)
    salt = base64.b64decode(salt_b64.encode())
    expected = base64.b64decode(digest_b64.encode())
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(candidate, expected)


class AuthService:
    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository

    def register(self, email: str, password: str, plan_type: str = "free") -> User:
        if not email.strip():
            raise ValidationError("Email is required.")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        if self.repository.get_user_by_email(email=email.strip().lower()):
            raise ConflictError("User already exists.")
        return self.repository.create_user(
            email=email.strip().lower(),
            password_hash=_hash_password(password),
            plan_type=plan_type,
        )

    def login(self, email: str, password: str) -> User:
        user = self.repository.get_user_by_email(email=email.strip().lower())
        if not user or not _verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")
        return user

    def change_password(self, user_id: int, current_password: str, new_password: str) -> User:
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")
        if not _verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        updated_user = self.repository.update_password(user_id, _hash_password(new_password))
        if not updated_user:
            raise NotFoundError("User not found.")
        return updated_user


class ChatService:
    def __init__(self, chat_repository: ChatRepository, auth_repository: AuthRepository) -> None:
        self.chat_repository = chat_repository
        self.auth_repository = auth_repository

    def create_thread(self, user_id: int, title: str) -> ChatThread:
        if not self.auth_repository.get_user_by_id(user_id):
            raise NotFoundError("User not found.")
        if not title.strip():
            raise ValidationError("Thread title is required.")
        return self.chat_repository.create_thread(user_id=user_id, title=title.strip())

    def list_threads(self, user_id: int) -> list[ChatThread]:
        return self.chat_repository.list_threads(user_id=user_id)

    def update_thread(self, user_id: int, thread_id: int, title: str) -> ChatThread:
        if not title.strip():
            raise ValidationError("Thread title is required.")
        thread = self.chat_repository.update_thread(user_id=user_id, thread_id=thread_id, title=title.strip())
        if not thread:
            raise NotFoundError("Chat thread not found.")
        return thread

    def delete_thread(self, user_id: int, thread_id: int) -> None:
        deleted = self.chat_repository.delete_thread(user_id=user_id, thread_id=thread_id)
        if not deleted:
            raise NotFoundError("Chat thread not found.")

    def add_message(
        self,
        user_id: int,
        thread_id: int,
        role: str,
        content: str,
        token_count: int = 0,
        model: str = "gpt-4.1-mini",
    ) -> ChatMessage:
        thread = self.chat_repository.get_thread(user_id=user_id, thread_id=thread_id)
        if not thread:
            raise NotFoundError("Chat thread not found.")
        if not content.strip():
            raise ValidationError("Message content is required.")
        return self.chat_repository.create_message(
            thread_id=thread_id,
            role=role,
            content=content.strip(),
            token_count=token_count,
            model=model,
        )

    def list_messages(self, user_id: int, thread_id: int) -> list[ChatMessage]:
        thread = self.chat_repository.get_thread(user_id=user_id, thread_id=thread_id)
        if not thread:
            raise NotFoundError("Chat thread not found.")
        return self.chat_repository.list_messages(thread_id=thread_id)

    def record_usage(
        self,
        user_id: int,
        thread_id: int | None,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        model: str,
        cost: float,
        timestamp: datetime | None = None,
    ) -> None:
        self.chat_repository.record_token_usage(
            user_id=user_id,
            thread_id=thread_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model=model,
            cost=cost,
            timestamp=timestamp,
        )


class RecordService:
    def __init__(self, repository: RecordRepository) -> None:
        self.repository = repository

    def create_record(
        self,
        user_id: str,
        domain: str,
        link: str | None = None,
        stored_path: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> Record:
        if not user_id.strip():
            raise ValidationError("User ID is required.")

        # Determine link_or_path from external link or internal stored path.
        link_stripped = link.strip() if link else None
        stored_path_stripped = stored_path.strip() if stored_path else None

        if link_stripped and stored_path_stripped:
            raise ValidationError("Provide either link or uploaded file, not both.")
        if not link_stripped and not stored_path_stripped:
            raise ValidationError("Either link or uploaded file is required.")

        link_or_path: str = link_stripped or stored_path_stripped  # type: ignore

        if not domain.strip():
            raise ValidationError("domain is required.")
        return self.repository.create_record(
            user_id=user_id.strip(),
            link_or_path=link_or_path,
            domain=domain.strip(),
            source=source.strip() if source else None,
            tags=tags,
            topics=topics,
        )

    def list_records(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        domain: str | None = None,
    ) -> list[Record]:
        return self.repository.list_records(user_id=user_id, tags=tags, topics=topics, domain=domain)

    def get_record(self, user_id: str, record_id: int) -> Record:
        record = self.repository.get_record(user_id=user_id, record_id=record_id)
        if not record:
            raise NotFoundError("Record not found.")
        return record

    def update_record(
        self,
        user_id: str,
        record_id: int,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> Record:
        updated = self.repository.update_record(
            user_id=user_id,
            record_id=record_id,
            link_or_path=None,
            source=None,
            domain=None,
            tags=tags,
            topics=topics,
        )
        if not updated:
            raise NotFoundError("Record not found.")
        return updated

    def delete_record(self, user_id: str, record_id: int) -> None:
        deleted = self.repository.delete_record(user_id=user_id, record_id=record_id)
        if not deleted:
            raise NotFoundError("Record not found.")

    def fetch_user_records(self, user_id: str) -> list[dict[str, object]]:
        return self.repository.fetch_user_records(user_id=user_id)

    def update_record_tags(self, record_id: int, user_id: str, new_tags: list[str]) -> dict[str, bool]:
        updated = self.repository.update_tags(record_id=record_id, user_id=user_id, new_tags=new_tags)
        if not updated:
            raise NotFoundError("Record not found.")
        return {"updated": True}

    def update_record_topics(self, record_id: int, user_id: str, new_topics: list[str]) -> dict[str, bool]:
        updated = self.repository.update_topics(record_id=record_id, user_id=user_id, new_topics=new_topics)
        if not updated:
            raise NotFoundError("Record not found.")
        return {"updated": True}

    def get_records_by_tags(self, user_id: str, tags: list[str]) -> list[dict[str, object]]:
        return self.repository.get_records_by_tags(user_id=user_id, tags=tags)

    def search_records(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        domain: str | None = None,
    ) -> list[dict[str, object]]:
        return self.repository.search_records(user_id=user_id, tags=tags, topics=topics, domain=domain)


class WorkItemService:
    def __init__(self, repository: WorkItemRepository) -> None:
        self.repository = repository

    def create_workitem(self, user_id: str, **payload: object) -> WorkItem:
        title = str(payload.get("title", "")).strip()
        if not user_id.strip():
            raise ValidationError("User ID is required.")
        if not title:
            raise ValidationError("title is required.")
        return self.repository.create_workitem(user_id=user_id.strip(), **payload)

    def list_workitems(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[WorkItem]:
        return self.repository.list_workitems(user_id=user_id, tags=tags, topics=topics)

    def get_workitem(self, user_id: str, workitem_id: int) -> WorkItem:
        workitem = self.repository.get_workitem(user_id=user_id, workitem_id=workitem_id)
        if not workitem:
            raise NotFoundError("Workitem not found.")
        return workitem

    def update_workitem(self, user_id: str, workitem_id: int, **payload: object) -> WorkItem:
        updated = self.repository.update_workitem(user_id=user_id, workitem_id=workitem_id, **payload)
        if not updated:
            raise NotFoundError("Workitem not found.")
        return updated

    def delete_workitem(self, user_id: str, workitem_id: int) -> None:
        deleted = self.repository.delete_workitem(user_id=user_id, workitem_id=workitem_id)
        if not deleted:
            raise NotFoundError("Workitem not found.")


class TimelineService:
    def __init__(self, repository: TimelineRepository) -> None:
        self.repository = repository

    def create_timeline_event(self, user_id: str, **payload: object) -> TimelineEvent:
        title = str(payload.get("title", "")).strip()
        if not user_id.strip():
            raise ValidationError("User ID is required.")
        if not title:
            raise ValidationError("title is required.")
        event_type = str(payload.get("event_type", "")).strip()
        if not event_type:
            raise ValidationError("event_type is required.")
        return self.repository.create_timeline_event(user_id=user_id.strip(), **payload)

    def list_timeline_events(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[TimelineEvent]:
        return self.repository.list_timeline_events(user_id=user_id, tags=tags, topics=topics)

    def get_timeline_event(self, user_id: str, event_id: int) -> TimelineEvent:
        timeline_event = self.repository.get_timeline_event(user_id=user_id, event_id=event_id)
        if not timeline_event:
            raise NotFoundError("Timeline event not found.")
        return timeline_event

    def update_timeline_event(self, user_id: str, event_id: int, **payload: object) -> TimelineEvent:
        updated = self.repository.update_timeline_event(user_id=user_id, event_id=event_id, **payload)
        if not updated:
            raise NotFoundError("Timeline event not found.")
        return updated

    def delete_timeline_event(self, user_id: str, event_id: int) -> None:
        deleted = self.repository.delete_timeline_event(user_id=user_id, event_id=event_id)
        if not deleted:
            raise NotFoundError("Timeline event not found.")


class IngestionService:
    def __init__(self, records_root: Path | None = None) -> None:
        self.records_root = records_root or Path(__file__).resolve().parents[2] / "records"

    def list_supported_types(self) -> list[str]:
        if not self.records_root.exists():
            return []
        return sorted([folder.name for folder in self.records_root.iterdir() if folder.is_dir()])

    def ingest_file(self, record_type: str, file_name: str, file_content: bytes) -> dict[str, str | int]:
        normalized_type = record_type.strip().lower()
        if not normalized_type:
            raise ValidationError("type is required.")

        supported_types = self.list_supported_types()
        if normalized_type not in supported_types:
            raise ValidationError(f"Unsupported type '{record_type}'. Supported types: {', '.join(supported_types)}")

        safe_name = Path(file_name).name.strip()
        if not safe_name:
            raise ValidationError("Uploaded file name is required.")
        if not file_content:
            raise ValidationError("Uploaded file is empty.")

        destination_dir = self.records_root / normalized_type
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = self._next_available_path(destination_dir / safe_name)
        destination_path.write_bytes(file_content)
        relative_stored_path = destination_path.relative_to(self.records_root.parent).as_posix()

        chunks = self._chunk_for_type(normalized_type, destination_path)
        return {
            "file_name": destination_path.name,
            "stored_path": str(relative_stored_path),
            "record_type": normalized_type,
            "chunk_count": len(chunks),
        }

    def _next_available_path(self, path: Path) -> Path:
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        counter = 1
        while True:
            candidate = path.with_name(f"{stem}_{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _chunk_for_type(self, record_type: str, file_path: Path) -> list[dict[str, object]]:
        try:
            if record_type == "generic":
                from src.utilities.chunking.generic_chunker import chunk_file

                return chunk_file(str(file_path))

            if record_type == "papers":
                from src.utilities.chunking.paper_based_chunking import chunk_research_paper

                return chunk_research_paper(str(file_path))

            if record_type == "pdfs":
                from src.utilities.chunking.pdf_chunking import semantic_pdf_chunking

                return semantic_pdf_chunking(str(file_path))

            if record_type == "self-notes":
                from src.utilities.chunking.self_notes_chunking import chunk_markdown_note

                return chunk_markdown_note(str(file_path))

            if record_type == "transcripts":
                from src.utilities.chunking.srt_chunker import chunk_srt_transcript

                return chunk_srt_transcript(str(file_path))

            return []
        except Exception as exc:
            raise ValidationError(f"Chunking failed for type '{record_type}': {exc}") from exc


class UserNotesService:
    def __init__(self, repository: UserNotesRepository) -> None:
        self.repository = repository

    def insert_note(
        self,
        user_id: str,
        md_file_path: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> dict[str, int]:
        if not user_id.strip():
            raise ValidationError("User ID is required.")
        if not md_file_path.strip():
            raise ValidationError("md_file_path is required.")
        note_id = self.repository.insert_note(
            user_id=user_id.strip(),
            md_file_path=md_file_path.strip(),
            tags=tags,
            topics=topics,
            embedding=embedding,
        )
        return {"note_id": note_id}

    def search_notes(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, object]]:
        if not user_id.strip():
            raise ValidationError("User ID is required.")
        if not query.strip():
            raise ValidationError("query is required.")
        return self.repository.search_notes(user_id=user_id.strip(), query=query.strip(), limit=limit)

    def retrieve_notes(self, user_id: str, query: str) -> list[dict[str, object]]:
        if not user_id.strip():
            raise ValidationError("User ID is required.")
        if not query.strip():
            raise ValidationError("query is required.")
        return self.repository.retrieve_notes(user_id=user_id.strip(), query=query.strip())

    def build_notes_graph(self, user_id: str) -> dict[str, list[dict[str, object]]]:
        if not user_id.strip():
            raise ValidationError("User ID is required.")
        return self.repository.build_notes_graph(user_id=user_id.strip())


class ResponseGeneratorService:
    def answer_question(
        self,
        query: str,
        graph_results: list[dict[str, object]],
        vector_results: list[dict[str, object]],
    ) -> dict[str, str]:
        if not query.strip():
            raise ValidationError("query is required.")

        try:
            from src.utilities.response_generator import answer_question

            return answer_question(query=query, graph_results=graph_results, vector_results=vector_results)
        except Exception as exc:
            raise ValidationError(f"Response generation failed: {exc}") from exc
