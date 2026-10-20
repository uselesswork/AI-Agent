from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.core.config import get_settings
from app.models.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationUpdate,
)
from app.services.application_repository import (
    ApplicationNotFoundError,
    ApplicationRepository,
)

router = APIRouter(prefix="/api/applications", tags=["投递管理"])


@lru_cache
def get_repository() -> ApplicationRepository:
    return ApplicationRepository(get_settings().validated_database_url())


@router.post("", response_model=ApplicationDetail, status_code=status.HTTP_201_CREATED)
def create_application(data: ApplicationCreate) -> ApplicationDetail:
    return get_repository().create(data)


@router.get("", response_model=list[ApplicationSummary])
def list_applications(
    application_status: ApplicationStatus | None = Query(default=None, alias="status"),
    sort: Literal["updated_desc", "score_desc", "score_asc"] = "updated_desc",
) -> list[ApplicationSummary]:
    return get_repository().list(application_status, sort)


@router.get("/{record_id}", response_model=ApplicationDetail)
def get_application(record_id: int) -> ApplicationDetail:
    try:
        return get_repository().get(record_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.patch("/{record_id}", response_model=ApplicationDetail)
def update_application(record_id: int, data: ApplicationUpdate) -> ApplicationDetail:
    try:
        return get_repository().update(record_id, data)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(record_id: int) -> Response:
    try:
        get_repository().delete(record_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
