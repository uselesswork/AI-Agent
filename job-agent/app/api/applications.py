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
from app.models.draft import ApplicationDraft
from app.services.application_repository import (
    ApplicationNotFoundError,
    ApplicationRepository,
)
from app.services.draft_composer import compose_draft
from app.services.draft_exporter import PdfFontUnavailableError, export_docx, export_pdf

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


@router.get("/{record_id}/draft", response_model=ApplicationDraft)
def get_application_draft(record_id: int) -> ApplicationDraft:
    return compose_draft(get_application(record_id))


@router.get("/{record_id}/draft/{kind}.{file_format}")
def download_application_draft(
    record_id: int, kind: Literal["resume", "letter"],
    file_format: Literal["docx", "pdf"],
) -> Response:
    draft = get_application_draft(record_id)
    document = draft.resume if kind == "resume" else draft.cover_letter
    try:
        content = export_docx(document) if file_format == "docx" else export_pdf(document)
    except PdfFontUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if file_format == "docx" else "application/pdf"
    )
    filename = f"application-{record_id}-{kind}.{file_format}"
    return Response(content=content, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    })


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
