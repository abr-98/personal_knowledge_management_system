from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from src.api.dependencies import (
    get_auth_service,
    get_chat_service,
    get_ingestion_service,
    get_record_service,
    get_timeline_service,
    get_workitem_service,
)
from src.api.schemas import (
    ChangePasswordRequest,
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatThreadCreateRequest,
    ChatThreadResponse,
    ChatThreadUpdateRequest,
    DeleteResponse,
    LoginRequest,
    RecordUploadRequest,
    RecordType,
    RecordUploadResponse,
    RecordResponse,
    RecordUpdateRequest,
    RegisterRequest,
    TimelineEventCreateRequest,
    TimelineEventResponse,
    TimelineEventUpdateRequest,
    TokenUsageRequest,
    UserResponse,
    WorkItemCreateRequest,
    WorkItemResponse,
    WorkItemUpdateRequest,
    WorkItemOptionsResponse,
)
from src.application.services import AuthService, ChatService, IngestionService, RecordService, TimelineService, WorkItemService
from src.domain.entities import WorkItemStatus, WorkItemPriority
from src.domain.errors import ValidationError


auth_router = APIRouter(prefix="/auth", tags=["auth"])
chat_router = APIRouter(prefix="/chat", tags=["chat"])
records_router = APIRouter(prefix="/records", tags=["records"])
workitems_router = APIRouter(prefix="/workitems", tags=["workitems"])
timelines_router = APIRouter(prefix="/timelines", tags=["timelines"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> UserResponse:
    return service.register(email=payload.email, password=payload.password, plan_type=payload.plan_type)


@auth_router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> UserResponse:
    return service.login(email=payload.email, password=payload.password)


@auth_router.put("/users/{user_id}/password", response_model=UserResponse)
def change_password(
    user_id: int,
    payload: ChangePasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    return service.change_password(
        user_id=user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )


@chat_router.post("/threads", response_model=ChatThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: ChatThreadCreateRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatThreadResponse:
    return service.create_thread(user_id=payload.user_id, title=payload.title)


@chat_router.get("/threads", response_model=list[ChatThreadResponse])
def list_threads(user_id: int, service: ChatService = Depends(get_chat_service)) -> list[ChatThreadResponse]:
    return service.list_threads(user_id=user_id)


@chat_router.put("/threads/{thread_id}", response_model=ChatThreadResponse)
def update_thread(
    thread_id: int,
    user_id: int,
    payload: ChatThreadUpdateRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatThreadResponse:
    return service.update_thread(user_id=user_id, thread_id=thread_id, title=payload.title)


@chat_router.delete("/threads/{thread_id}", response_model=DeleteResponse)
def delete_thread(
    thread_id: int,
    user_id: int,
    service: ChatService = Depends(get_chat_service),
) -> DeleteResponse:
    service.delete_thread(user_id=user_id, thread_id=thread_id)
    return DeleteResponse()


@chat_router.post(
    "/threads/{thread_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    thread_id: int,
    user_id: int,
    payload: ChatMessageCreateRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    return service.add_message(
        user_id=user_id,
        thread_id=thread_id,
        role=payload.role,
        content=payload.content,
        token_count=payload.token_count,
        model=payload.model,
    )


@chat_router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageResponse])
def list_messages(
    thread_id: int,
    user_id: int,
    service: ChatService = Depends(get_chat_service),
) -> list[ChatMessageResponse]:
    return service.list_messages(user_id=user_id, thread_id=thread_id)


@chat_router.post("/token-usage", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def record_token_usage(
    payload: TokenUsageRequest,
    service: ChatService = Depends(get_chat_service),
) -> None:
    service.record_usage(
        user_id=payload.user_id,
        thread_id=payload.thread_id,
        input_tokens=payload.input_tokens,
        output_tokens=payload.output_tokens,
        total_tokens=payload.total_tokens,
        model=payload.model,
        cost=payload.cost,
        timestamp=payload.timestamp,
    )


@records_router.post("", response_model=RecordResponse | RecordUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_or_create_record(
    user_id: str = Form(...),
    domain: str | None = Form(None),
    source: str | None = Form(None),
    link: str | None = Form(None),
    record_type: RecordType | None = Form(None),
    report_type: RecordType | None = Form(None),
    type_alias: RecordType | None = Form(None, alias="type"),
    file: UploadFile | None = File(None),
    tags: list[str] = Form(default_factory=list),
    topics: list[str] = Form(default_factory=list),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    record_service: RecordService = Depends(get_record_service),
) -> RecordResponse | RecordUploadResponse:
    """
    Unified endpoint for uploading files or creating records with links.

    - If file is provided: saves under records/<type>/ and stores relative path in DB
    - If link is provided: creates a record with the external link
    - Either file OR link must be provided, not both
    """
    # Handle file upload
    if file:
        resolved_record_type = record_type or report_type or type_alias
        if not resolved_record_type and domain:
            try:
                resolved_record_type = RecordType(domain)
            except ValueError:
                resolved_record_type = None

        if not resolved_record_type:
            raise ValidationError("record_type is required when uploading a file.")
        if link:
            raise ValidationError("Provide either a file OR link, not both.")
        
        content = await file.read()
        result = ingestion_service.ingest_file(
            record_type=resolved_record_type.value,
            file_name=file.filename or "",
            file_content=content,
        )

        record = record_service.create_record(
            user_id=user_id,
            stored_path=result["stored_path"],  # type: ignore
            domain=result.get("record_type", resolved_record_type.value),  # type: ignore
            source=source or "upload",
            tags=tags,
            topics=topics,
        )
        
        # Return both upload response and record
        response_data = {
            **result,
            "id": record.id,
            "user_id": record.user_id,
        }
        return RecordUploadResponse(**result)

    # Handle link record creation
    else:
        if domain is None:
            raise ValidationError("domain is required when creating a link record.")
        record = record_service.create_record(
            user_id=user_id,
            link=link,
            domain=domain,
            source=source,
            tags=tags,
            topics=topics,
        )
        return record


@records_router.get("", response_model=list[RecordResponse])
def list_records(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    domain: str | None = None,
    service: RecordService = Depends(get_record_service),
) -> list[RecordResponse]:
    return service.list_records(user_id=user_id, tags=tags, topics=topics, domain=domain)


@records_router.get("/{record_id}", response_model=RecordResponse)
def get_record(
    record_id: int,
    user_id: str,
    service: RecordService = Depends(get_record_service),
) -> RecordResponse:
    return service.get_record(user_id=user_id, record_id=record_id)


@records_router.put("/{record_id}", response_model=RecordResponse)
def update_record(
    record_id: int,
    user_id: str,
    payload: RecordUpdateRequest,
    service: RecordService = Depends(get_record_service),
) -> RecordResponse:
    return service.update_record(user_id=user_id, record_id=record_id, **payload.model_dump(exclude_none=True))


@records_router.delete("/{record_id}", response_model=DeleteResponse)
def delete_record(
    record_id: int,
    user_id: str,
    service: RecordService = Depends(get_record_service),
) -> DeleteResponse:
    service.delete_record(user_id=user_id, record_id=record_id)
    return DeleteResponse()


@workitems_router.get("/options", response_model=WorkItemOptionsResponse)
def get_workitem_options() -> WorkItemOptionsResponse:
    """Get available status and priority options for work items."""
    return WorkItemOptionsResponse(
        statuses=[status.value for status in WorkItemStatus],
        priorities=[priority.value for priority in WorkItemPriority],
    )


@workitems_router.post("", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED)
def create_workitem(
    payload: WorkItemCreateRequest,
    status: WorkItemStatus = WorkItemStatus.PENDING,
    priority: WorkItemPriority = WorkItemPriority.MEDIUM,
    service: WorkItemService = Depends(get_workitem_service),
) -> WorkItemResponse:
    return service.create_workitem(
        user_id=payload.user_id,
        status=status,
        priority=priority,
        **payload.model_dump(exclude={"user_id"}),
    )


@workitems_router.get("", response_model=list[WorkItemResponse])
def list_workitems(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    service: WorkItemService = Depends(get_workitem_service),
) -> list[WorkItemResponse]:
    return service.list_workitems(user_id=user_id, tags=tags, topics=topics)


@workitems_router.get("/{workitem_id}", response_model=WorkItemResponse)
def get_workitem(
    workitem_id: int,
    user_id: str,
    service: WorkItemService = Depends(get_workitem_service),
) -> WorkItemResponse:
    return service.get_workitem(user_id=user_id, workitem_id=workitem_id)


@workitems_router.put("/{workitem_id}", response_model=WorkItemResponse)
def update_workitem(
    workitem_id: int,
    user_id: str,
    payload: WorkItemUpdateRequest,
    status: WorkItemStatus | None = None,
    priority: WorkItemPriority | None = None,
    service: WorkItemService = Depends(get_workitem_service),
) -> WorkItemResponse:
    update_data = payload.model_dump(exclude_none=True)
    if status is not None:
        update_data["status"] = status
    if priority is not None:
        update_data["priority"] = priority
    return service.update_workitem(user_id=user_id, workitem_id=workitem_id, **update_data)


@workitems_router.delete("/{workitem_id}", response_model=DeleteResponse)
def delete_workitem(
    workitem_id: int,
    user_id: str,
    service: WorkItemService = Depends(get_workitem_service),
) -> DeleteResponse:
    service.delete_workitem(user_id=user_id, workitem_id=workitem_id)
    return DeleteResponse()


@timelines_router.post("", response_model=TimelineEventResponse, status_code=status.HTTP_201_CREATED)
def create_timeline_event(
    payload: TimelineEventCreateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineEventResponse:
    return service.create_timeline_event(user_id=payload.user_id, **payload.model_dump(exclude={"user_id"}))


@timelines_router.get("", response_model=list[TimelineEventResponse])
def list_timeline_events(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    service: TimelineService = Depends(get_timeline_service),
) -> list[TimelineEventResponse]:
    return service.list_timeline_events(user_id=user_id, tags=tags, topics=topics)


@timelines_router.get("/{event_id}", response_model=TimelineEventResponse)
def get_timeline_event(
    event_id: int,
    user_id: str,
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineEventResponse:
    return service.get_timeline_event(user_id=user_id, event_id=event_id)


@timelines_router.put("/{event_id}", response_model=TimelineEventResponse)
def update_timeline_event(
    event_id: int,
    user_id: str,
    payload: TimelineEventUpdateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineEventResponse:
    return service.update_timeline_event(user_id=user_id, event_id=event_id, **payload.model_dump(exclude_none=True))


@timelines_router.delete("/{event_id}", response_model=DeleteResponse)
def delete_timeline_event(
    event_id: int,
    user_id: str,
    service: TimelineService = Depends(get_timeline_service),
) -> DeleteResponse:
    service.delete_timeline_event(user_id=user_id, event_id=event_id)
    return DeleteResponse()


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(records_router)
api_router.include_router(workitems_router)
api_router.include_router(timelines_router)