from __future__ import annotations

from datetime import datetime
from typing import Any

from src.domain.entities import ChatMessage, ChatThread, Record, TimelineEvent, User, WorkItem
from src.domain.errors import ValidationError
from src.infrastructure.database import DatabaseSettings, get_connection, load_database_settings
from src.utilities.manual_tag_handling.fetch_by_tags import search_records as utility_search_records
from src.utilities.manual_tag_handling.query_manual_tags import (
    fetch_user_records as utility_fetch_user_records,
    get_records_by_tags as utility_get_records_by_tags,
    update_tags as utility_update_tags,
    update_topics as utility_update_topics,
)
from src.utilities.self_notes_handling.build_note_graph import build_notes_graph as utility_build_notes_graph
from src.utilities.self_notes_handling.self_note_db_interactions import (
    insert_note as utility_insert_note,
    retrieve_notes as utility_retrieve_notes,
    search_notes as utility_search_notes,
)


def _as_list(value: list[Any] | None) -> list[Any]:
    return value or []


class PostgresRepository:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self.settings = settings or load_database_settings()

    def _connect(self):
        return get_connection(self.settings)


class PostgresAuthRepository(PostgresRepository):
    def create_user(self, email: str, password_hash: str, plan_type: str = "free") -> User:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, plan_type)
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (email, password_hash, plan_type),
                )
                row = cur.fetchone()
        return User(**row)

    def get_user_by_email(self, email: str) -> User | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                row = cur.fetchone()
        return User(**row) if row else None

    def get_user_by_id(self, user_id: int) -> User | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
        return User(**row) if row else None

    def update_password(self, user_id: int, password_hash: str) -> User | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (password_hash, user_id),
                )
                row = cur.fetchone()
        return User(**row) if row else None


class PostgresChatRepository(PostgresRepository):
    def create_thread(self, user_id: int, title: str) -> ChatThread:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_threads (user_id, title)
                    VALUES (%s, %s)
                    RETURNING *
                    """,
                    (user_id, title),
                )
                row = cur.fetchone()
        return ChatThread(**row)

    def list_threads(self, user_id: int) -> list[ChatThread]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM chat_threads WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
                rows = cur.fetchall()
        return [ChatThread(**row) for row in rows]

    def get_thread(self, user_id: int, thread_id: int) -> ChatThread | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM chat_threads WHERE id = %s AND user_id = %s",
                    (thread_id, user_id),
                )
                row = cur.fetchone()
        return ChatThread(**row) if row else None

    def update_thread(self, user_id: int, thread_id: int, title: str) -> ChatThread | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE chat_threads
                    SET title = %s
                    WHERE id = %s AND user_id = %s
                    RETURNING *
                    """,
                    (title, thread_id, user_id),
                )
                row = cur.fetchone()
        return ChatThread(**row) if row else None

    def delete_thread(self, user_id: int, thread_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chat_threads WHERE id = %s AND user_id = %s", (thread_id, user_id))
                return cur.rowcount > 0

    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        token_count: int = 0,
        model: str = "gpt-4.1-mini",
    ) -> ChatMessage:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (thread_id, role, content, token_count, model)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (thread_id, role, content, token_count, model),
                )
                row = cur.fetchone()
        return ChatMessage(**row)

    def list_messages(self, thread_id: int) -> list[ChatMessage]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM messages WHERE thread_id = %s ORDER BY created_at ASC",
                    (thread_id,),
                )
                rows = cur.fetchall()
        return [ChatMessage(**row) for row in rows]

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
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO token_usage (
                        user_id,
                        thread_id,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        model,
                        cost,
                        timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))
                    """,
                    (user_id, thread_id, input_tokens, output_tokens, total_tokens, model, cost, timestamp),
                )


class PostgresRecordRepository(PostgresRepository):
    def create_record(
        self,
        user_id: str,
        link_or_path: str,
        domain: str,
        source: str | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> Record:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO records (user_id, link_or_path, source, tags, domain, topics)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (user_id, link_or_path, source, tags, domain, topics),
                )
                row = cur.fetchone()
        return Record(
            id=row["id"],
            user_id=row["user_id"],
            link_or_path=row["link_or_path"],
            created_at=row["created_at"],
            domain=row["domain"],
            source=row.get("source"),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
        )

    def list_records(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        domain: str | None = None,
    ) -> list[Record]:
        query = """
            SELECT *
            FROM records
            WHERE user_id = %s
        """
        params: list[Any] = [user_id]
        if tags:
            query += " AND tags && %s"
            params.append(tags)
        if topics:
            query += " AND topics && %s"
            params.append(topics)
        if domain:
            query += " AND domain = %s"
            params.append(domain)
        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        return [
            Record(
                id=row["id"],
                user_id=row["user_id"],
                link_or_path=row["link_or_path"],
                created_at=row["created_at"],
                domain=row["domain"],
                source=row.get("source"),
                tags=_as_list(row.get("tags")),
                topics=_as_list(row.get("topics")),
            )
            for row in rows
        ]

    def get_record(self, user_id: str, record_id: int) -> Record | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM records WHERE id = %s AND user_id = %s",
                    (record_id, user_id),
                )
                row = cur.fetchone()
        if not row:
            return None
        return Record(
            id=row["id"],
            user_id=row["user_id"],
            link_or_path=row["link_or_path"],
            created_at=row["created_at"],
            domain=row["domain"],
            source=row.get("source"),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
        )

    def update_record(
        self,
        user_id: str,
        record_id: int,
        link_or_path: str | None = None,
        source: str | None = None,
        domain: str | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> Record | None:
        fields: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("link_or_path", link_or_path),
            ("source", source),
            ("domain", domain),
            ("tags", tags),
            ("topics", topics),
        ):
            if value is not None:
                fields.append(f"{column} = %s")
                values.append(value)
        if not fields:
            raise ValidationError("At least one record field must be provided for update.")

        values.extend([record_id, user_id])
        query = f"UPDATE records SET {', '.join(fields)} WHERE id = %s AND user_id = %s RETURNING *"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                row = cur.fetchone()
        if not row:
            return None
        return Record(
            id=row["id"],
            user_id=row["user_id"],
            link_or_path=row["link_or_path"],
            created_at=row["created_at"],
            domain=row["domain"],
            source=row.get("source"),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
        )

    def delete_record(self, user_id: str, record_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM records WHERE id = %s AND user_id = %s", (record_id, user_id))
                return cur.rowcount > 0

    def fetch_user_records(self, user_id: str) -> list[dict[str, object]]:
        return utility_fetch_user_records(user_id=user_id, settings=self.settings)

    def update_tags(self, record_id: int, user_id: str, new_tags: list[str]) -> bool:
        return utility_update_tags(record_id=record_id, user_id=user_id, new_tags=new_tags, settings=self.settings)

    def update_topics(self, record_id: int, user_id: str, new_topics: list[str]) -> bool:
        return utility_update_topics(
            record_id=record_id,
            user_id=user_id,
            new_topics=new_topics,
            settings=self.settings,
        )

    def get_records_by_tags(self, user_id: str, tags: list[str]) -> list[dict[str, object]]:
        return utility_get_records_by_tags(user_id=user_id, tags=tags, settings=self.settings)

    def search_records(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        domain: str | None = None,
    ) -> list[dict[str, object]]:
        return utility_search_records(
            user_id=user_id,
            tags=tags,
            topics=topics,
            domain=domain,
            settings=self.settings,
        )


class PostgresUserNotesRepository(PostgresRepository):
    def insert_note(
        self,
        user_id: str,
        md_file_path: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> int:
        return utility_insert_note(
            user_id=user_id,
            md_file_path=md_file_path,
            tags=tags,
            topics=topics,
            embedding=embedding,
            settings=self.settings,
        )

    def search_notes(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, object]]:
        return utility_search_notes(user_id=user_id, query=query, limit=limit, settings=self.settings)

    def retrieve_notes(self, user_id: str, query: str) -> list[dict[str, object]]:
        return utility_retrieve_notes(user_id=user_id, query=query, settings=self.settings)

    def build_notes_graph(self, user_id: str) -> dict[str, list[dict[str, object]]]:
        return utility_build_notes_graph(user_id=user_id, settings=self.settings)


class PostgresWorkItemRepository(PostgresRepository):
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
    ) -> WorkItem:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workitems (
                        user_id, title, description, status, priority, related_notes, tags, topics, due_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (user_id, title, description, status, priority, related_notes, tags, topics, due_date),
                )
                row = cur.fetchone()
        return WorkItem(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            description=row.get("description"),
            status=row["status"],
            priority=row["priority"],
            related_notes=_as_list(row.get("related_notes")),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
            due_date=row.get("due_date"),
        )

    def list_workitems(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[WorkItem]:
        query = "SELECT * FROM workitems WHERE user_id = %s"
        params: list[Any] = [user_id]
        if tags:
            query += " AND tags && %s"
            params.append(tags)
        if topics:
            query += " AND topics && %s"
            params.append(topics)
        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        return [
            WorkItem(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                description=row.get("description"),
                status=row["status"],
                priority=row["priority"],
                related_notes=_as_list(row.get("related_notes")),
                tags=_as_list(row.get("tags")),
                topics=_as_list(row.get("topics")),
                due_date=row.get("due_date"),
            )
            for row in rows
        ]

    def get_workitem(self, user_id: str, workitem_id: int) -> WorkItem | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM workitems WHERE id = %s AND user_id = %s", (workitem_id, user_id))
                row = cur.fetchone()
        if not row:
            return None
        return WorkItem(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            description=row.get("description"),
            status=row["status"],
            priority=row["priority"],
            related_notes=_as_list(row.get("related_notes")),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
            due_date=row.get("due_date"),
        )

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
    ) -> WorkItem | None:
        fields: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("title", title),
            ("description", description),
            ("status", status),
            ("priority", priority),
            ("related_notes", related_notes),
            ("tags", tags),
            ("topics", topics),
            ("due_date", due_date),
        ):
            if value is not None:
                fields.append(f"{column} = %s")
                values.append(value)
        if not fields:
            raise ValidationError("At least one workitem field must be provided for update.")

        fields.append("updated_at = NOW()")
        values.extend([workitem_id, user_id])
        query = f"UPDATE workitems SET {', '.join(fields)} WHERE id = %s AND user_id = %s RETURNING *"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                row = cur.fetchone()
        if not row:
            return None
        return WorkItem(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            description=row.get("description"),
            status=row["status"],
            priority=row["priority"],
            related_notes=_as_list(row.get("related_notes")),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
            due_date=row.get("due_date"),
        )

    def delete_workitem(self, user_id: str, workitem_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM workitems WHERE id = %s AND user_id = %s", (workitem_id, user_id))
                return cur.rowcount > 0


class PostgresTimelineRepository(PostgresRepository):
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
    ) -> TimelineEvent:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO timelines (
                        user_id, event_type, title, description, related_notes, related_workitems, tags, topics
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (user_id, event_type, title, description, related_notes, related_workitems, tags, topics),
                )
                row = cur.fetchone()
        return TimelineEvent(
            id=row["id"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            event_type=row.get("event_type"),
            title=row.get("title"),
            description=row.get("description"),
            related_notes=_as_list(row.get("related_notes")),
            related_workitems=_as_list(row.get("related_workitems")),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
        )

    def list_timeline_events(
        self,
        user_id: str,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[TimelineEvent]:
        query = "SELECT * FROM timelines WHERE user_id = %s"
        params: list[Any] = [user_id]
        if tags:
            query += " AND tags && %s"
            params.append(tags)
        if topics:
            query += " AND topics && %s"
            params.append(topics)
        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        return [
            TimelineEvent(
                id=row["id"],
                user_id=row["user_id"],
                created_at=row["created_at"],
                event_type=row.get("event_type"),
                title=row.get("title"),
                description=row.get("description"),
                related_notes=_as_list(row.get("related_notes")),
                related_workitems=_as_list(row.get("related_workitems")),
                tags=_as_list(row.get("tags")),
                topics=_as_list(row.get("topics")),
            )
            for row in rows
        ]

    def get_timeline_event(self, user_id: str, event_id: int) -> TimelineEvent | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM timelines WHERE id = %s AND user_id = %s", (event_id, user_id))
                row = cur.fetchone()
        if not row:
            return None
        return TimelineEvent(
            id=row["id"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            event_type=row.get("event_type"),
            title=row.get("title"),
            description=row.get("description"),
            related_notes=_as_list(row.get("related_notes")),
            related_workitems=_as_list(row.get("related_workitems")),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
        )

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
    ) -> TimelineEvent | None:
        fields: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("event_type", event_type),
            ("title", title),
            ("description", description),
            ("related_notes", related_notes),
            ("related_workitems", related_workitems),
            ("tags", tags),
            ("topics", topics),
        ):
            if value is not None:
                fields.append(f"{column} = %s")
                values.append(value)
        if not fields:
            raise ValidationError("At least one timeline field must be provided for update.")

        values.extend([event_id, user_id])
        query = f"UPDATE timelines SET {', '.join(fields)} WHERE id = %s AND user_id = %s RETURNING *"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                row = cur.fetchone()
        if not row:
            return None
        return TimelineEvent(
            id=row["id"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            event_type=row.get("event_type"),
            title=row.get("title"),
            description=row.get("description"),
            related_notes=_as_list(row.get("related_notes")),
            related_workitems=_as_list(row.get("related_workitems")),
            tags=_as_list(row.get("tags")),
            topics=_as_list(row.get("topics")),
        )

    def delete_timeline_event(self, user_id: str, event_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM timelines WHERE id = %s AND user_id = %s", (event_id, user_id))
                return cur.rowcount > 0