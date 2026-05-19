from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.domain.errors import DomainError
from src.infrastructure.database import initialize_database
from src.mcp.serialization import serialize_for_mcp
from src.service_factory import (
    get_record_service,
    get_response_generator_service,
    get_timeline_service,
    get_user_notes_service,
    get_workitem_service,
)


mcp = FastMCP("pkms-chatbot")


def _success(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": serialize_for_mcp(data)}


def _wrap(operation):
    try:
        return _success(operation())
    except DomainError as exc:
        return {"ok": False, "error": str(exc)}


def _chatbot_context(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    record_service = get_record_service()
    workitem_service = get_workitem_service()
    timeline_service = get_timeline_service()

    return {
        "records": record_service.list_records(user_id=user_id, tags=tags, topics=topics, domain=domain),
        "workitems": workitem_service.list_workitems(user_id=user_id, tags=tags, topics=topics),
        "timeline_events": timeline_service.list_timeline_events(user_id=user_id, tags=tags, topics=topics),
    }


@mcp.tool()
def health() -> dict[str, Any]:
    """Return MCP server health information for chatbot clients."""
    return _success({"status": "ok", "server": "pkms-chatbot-mcp"})


@mcp.tool()
def generate_response(
    query: str,
    graph_results: list[dict[str, object]],
    vector_results: list[dict[str, object]],
) -> dict[str, Any]:
    """Generate an answer from retrieved graph/vector memory using the response generator."""
    return _wrap(
        lambda: get_response_generator_service().answer_question(
            query=query,
            graph_results=graph_results,
            vector_results=vector_results,
        )
    )


@mcp.tool()
def insert_user_note(
    user_id: str,
    md_file_path: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Insert a markdown note into the notes store."""
    return _wrap(
        lambda: get_user_notes_service().insert_note(
            user_id=user_id,
            md_file_path=md_file_path,
            tags=tags,
            topics=topics,
        )
    )


@mcp.tool()
def search_user_notes(user_id: str, query: str, limit: int = 5) -> dict[str, Any]:
    """Search notes with full-text ranking."""
    return _wrap(lambda: get_user_notes_service().search_notes(user_id=user_id, query=query, limit=limit))


@mcp.tool()
def retrieve_user_notes(user_id: str, query: str) -> dict[str, Any]:
    """Retrieve notes by query and backlink expansion."""
    return _wrap(lambda: get_user_notes_service().retrieve_notes(user_id=user_id, query=query))


@mcp.tool()
def build_user_notes_graph(user_id: str) -> dict[str, Any]:
    """Build a graph view of user notes and backlinks."""
    return _wrap(lambda: get_user_notes_service().build_notes_graph(user_id=user_id))


@mcp.tool()
def fetch_user_records(user_id: str) -> dict[str, Any]:
    """Fetch all records for a user (manual tag utility-backed)."""
    return _wrap(lambda: get_record_service().fetch_user_records(user_id=user_id))


@mcp.tool()
def update_record_tags(user_id: str, record_id: int, tags: list[str]) -> dict[str, Any]:
    """Update manual tags for a record."""
    return _wrap(lambda: get_record_service().update_record_tags(record_id=record_id, user_id=user_id, new_tags=tags))


@mcp.tool()
def update_record_topics(user_id: str, record_id: int, topics: list[str]) -> dict[str, Any]:
    """Update manual topics for a record."""
    return _wrap(
        lambda: get_record_service().update_record_topics(record_id=record_id, user_id=user_id, new_topics=topics)
    )


@mcp.tool()
def get_records_by_tags(user_id: str, tags: list[str]) -> dict[str, Any]:
    """Fetch records that match any of the provided tags."""
    return _wrap(lambda: get_record_service().get_records_by_tags(user_id=user_id, tags=tags))


@mcp.tool()
def search_records_by_filters(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Search records using optional tags/topics/domain filters."""
    return _wrap(lambda: get_record_service().search_records(user_id=user_id, tags=tags, topics=topics, domain=domain))


@mcp.tool()
def create_record(
    user_id: str,
    link_or_path: str,
    domain: str,
    source: str | None = None,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Create a knowledge record for chatbot retrieval."""
    return _wrap(
        lambda: get_record_service().create_record(
            user_id=user_id,
            link_or_path=link_or_path,
            domain=domain,
            source=source,
            tags=tags,
            topics=topics,
        )
    )


@mcp.tool()
def list_records(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """List records available to the chatbot for a user."""
    return _wrap(lambda: get_record_service().list_records(user_id=user_id, tags=tags, topics=topics, domain=domain))


@mcp.tool()
def get_record(user_id: str, record_id: int) -> dict[str, Any]:
    """Fetch one record by ID."""
    return _wrap(lambda: get_record_service().get_record(user_id=user_id, record_id=record_id))


@mcp.tool()
def update_record(
    user_id: str,
    record_id: int,
    link_or_path: str | None = None,
    source: str | None = None,
    domain: str | None = None,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Update a knowledge record."""
    return _wrap(
        lambda: get_record_service().update_record(
            user_id=user_id,
            record_id=record_id,
            link_or_path=link_or_path,
            source=source,
            domain=domain,
            tags=tags,
            topics=topics,
        )
    )


@mcp.tool()
def delete_record(user_id: str, record_id: int) -> dict[str, Any]:
    """Delete a knowledge record."""
    return _wrap(lambda: _delete_record(user_id=user_id, record_id=record_id))


def _delete_record(user_id: str, record_id: int) -> dict[str, bool]:
    get_record_service().delete_record(user_id=user_id, record_id=record_id)
    return {"deleted": True}


@mcp.tool()
def create_workitem(
    user_id: str,
    title: str,
    description: str | None = None,
    status: str = "pending",
    priority: str = "medium",
    related_notes: list[str] | None = None,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    """Create a workitem that the chatbot can inspect or manage."""
    return _wrap(
        lambda: get_workitem_service().create_workitem(
            user_id=user_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            related_notes=related_notes,
            tags=tags,
            topics=topics,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
        )
    )


@mcp.tool()
def list_workitems(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """List workitems for chatbot planning flows."""
    return _wrap(lambda: get_workitem_service().list_workitems(user_id=user_id, tags=tags, topics=topics))


@mcp.tool()
def get_workitem(user_id: str, workitem_id: int) -> dict[str, Any]:
    """Fetch one workitem by ID."""
    return _wrap(lambda: get_workitem_service().get_workitem(user_id=user_id, workitem_id=workitem_id))


@mcp.tool()
def update_workitem(
    user_id: str,
    workitem_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    related_notes: list[str] | None = None,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    """Update a workitem."""
    return _wrap(
        lambda: get_workitem_service().update_workitem(
            user_id=user_id,
            workitem_id=workitem_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            related_notes=related_notes,
            tags=tags,
            topics=topics,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
        )
    )


@mcp.tool()
def delete_workitem(user_id: str, workitem_id: int) -> dict[str, Any]:
    """Delete a workitem."""
    return _wrap(lambda: _delete_workitem(user_id=user_id, workitem_id=workitem_id))


def _delete_workitem(user_id: str, workitem_id: int) -> dict[str, bool]:
    get_workitem_service().delete_workitem(user_id=user_id, workitem_id=workitem_id)
    return {"deleted": True}


@mcp.tool()
def create_timeline_event(
    user_id: str,
    event_type: str,
    title: str,
    description: str | None = None,
    related_notes: list[str] | None = None,
    related_workitems: list[int] | None = None,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Create a timeline event for chatbot memory or planning."""
    return _wrap(
        lambda: get_timeline_service().create_timeline_event(
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            related_notes=related_notes,
            related_workitems=related_workitems,
            tags=tags,
            topics=topics,
        )
    )


@mcp.tool()
def list_timeline_events(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """List timeline events for chatbot context assembly."""
    return _wrap(lambda: get_timeline_service().list_timeline_events(user_id=user_id, tags=tags, topics=topics))


@mcp.tool()
def get_timeline_event(user_id: str, event_id: int) -> dict[str, Any]:
    """Fetch one timeline event by ID."""
    return _wrap(lambda: get_timeline_service().get_timeline_event(user_id=user_id, event_id=event_id))


@mcp.tool()
def update_timeline_event(
    user_id: str,
    event_id: int,
    event_type: str | None = None,
    title: str | None = None,
    description: str | None = None,
    related_notes: list[str] | None = None,
    related_workitems: list[int] | None = None,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Update a timeline event."""
    return _wrap(
        lambda: get_timeline_service().update_timeline_event(
            user_id=user_id,
            event_id=event_id,
            event_type=event_type,
            title=title,
            description=description,
            related_notes=related_notes,
            related_workitems=related_workitems,
            tags=tags,
            topics=topics,
        )
    )


@mcp.tool()
def delete_timeline_event(user_id: str, event_id: int) -> dict[str, Any]:
    """Delete a timeline event."""
    return _wrap(lambda: _delete_timeline_event(user_id=user_id, event_id=event_id))


def _delete_timeline_event(user_id: str, event_id: int) -> dict[str, bool]:
    get_timeline_service().delete_timeline_event(user_id=user_id, event_id=event_id)
    return {"deleted": True}


@mcp.tool()
def get_chatbot_context(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Collect records, workitems, timelines for chatbot prompts."""
    return _wrap(
        lambda: _chatbot_context(
            user_id=user_id,
            tags=tags,
            topics=topics,
            domain=domain,
        )
    )


def main() -> None:
    initialize_database()
    mcp.run()


if __name__ == "__main__":
    main()