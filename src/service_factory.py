from __future__ import annotations

from functools import lru_cache

from src.application.services import (
    AuthService,
    ChatService,
    IngestionService,
    RecordService,
    ResponseGeneratorService,
    TimelineService,
    UserNotesService,
    WorkItemService,
)
from src.infrastructure.postgres_repositories import (
    PostgresAuthRepository,
    PostgresChatRepository,
    PostgresRecordRepository,
    PostgresTimelineRepository,
    PostgresUserNotesRepository,
    PostgresWorkItemRepository,
)


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(repository=PostgresAuthRepository())


@lru_cache
def get_chat_service() -> ChatService:
    auth_repository = PostgresAuthRepository()
    return ChatService(chat_repository=PostgresChatRepository(), auth_repository=auth_repository)


@lru_cache
def get_record_service() -> RecordService:
    return RecordService(repository=PostgresRecordRepository())


@lru_cache
def get_ingestion_service() -> IngestionService:
    return IngestionService()


@lru_cache
def get_user_notes_service() -> UserNotesService:
    return UserNotesService(repository=PostgresUserNotesRepository())


@lru_cache
def get_response_generator_service() -> ResponseGeneratorService:
    return ResponseGeneratorService()


@lru_cache
def get_workitem_service() -> WorkItemService:
    return WorkItemService(repository=PostgresWorkItemRepository())


@lru_cache
def get_timeline_service() -> TimelineService:
    return TimelineService(repository=PostgresTimelineRepository())