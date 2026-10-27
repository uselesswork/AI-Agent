from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query, Response, status
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.models.annotation import AnnotationDetail, AnnotationWrite, DocumentKind
from app.models.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationEvent,
    ApplicationPage,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationUpdate,
)
from app.models.draft import ApplicationDraft, DraftTemplate
from app.models.draft_version import (
    DraftReviewRequest, DraftVersionCreate, DraftVersionDetail, DraftVersionSummary,
)
from app.models.evidence import EvidenceReport, SourceStatus, VersionComparison
from app.services.application_repository import (
    ApplicationNotFoundError,
    ApplicationRepository,
)
from app.services.annotation_repository import AnnotationRepository
from app.services.draft_composer import compose_draft
from app.services.draft_exporter import PdfFontUnavailableError, export_docx, export_pdf
from app.services.draft_version_repository import (
    DraftVersionNotFoundError, DraftVersionRepository,
)
from app.services.evidence_checker import (
    check_version_evidence, compare_versions, literal_in_source,
)

router = APIRouter(prefix="/api/applications", tags=["投递管理"])


@lru_cache
def get_repository() -> ApplicationRepository:
    return ApplicationRepository(get_settings().validated_database_url())


def get_draft_repository() -> DraftVersionRepository:
    return DraftVersionRepository(get_repository().engine)


def get_annotation_repository() -> AnnotationRepository:
    return AnnotationRepository(get_repository().engine)


def _export_response(document, file_format: str, filename: str) -> Response:
    try:
        content = export_docx(document) if file_format == "docx" else export_pdf(document)
    except PdfFontUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if file_format == "docx" else "application/pdf"
    )
    return Response(content=content, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    })


@router.post("", response_model=ApplicationDetail, status_code=status.HTTP_201_CREATED)
def create_application(data: ApplicationCreate) -> ApplicationDetail:
    return get_repository().create(data)


@router.get("", response_model=list[ApplicationSummary])
def list_applications(
    application_status: ApplicationStatus | None = Query(default=None, alias="status"),
    sort: Literal["updated_desc", "score_desc", "score_asc"] = "updated_desc",
) -> list[ApplicationSummary]:
    return get_repository().list(application_status, sort)


@router.get("/search", response_model=ApplicationPage)
def search_applications(
    q: str = Query(default="", max_length=100),
    application_status: ApplicationStatus | None = Query(default=None, alias="status"),
    sort: Literal["updated_desc", "score_desc", "score_asc"] = "updated_desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> ApplicationPage:
    return get_repository().search(q.strip(), application_status, sort, page, page_size)


@router.get("/{record_id}", response_model=ApplicationDetail)
def get_application(record_id: int) -> ApplicationDetail:
    try:
        return get_repository().get(record_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.get("/{record_id}/events", response_model=list[ApplicationEvent])
def list_application_events(record_id: int) -> list[ApplicationEvent]:
    try:
        return get_repository().list_events(record_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.get("/{record_id}/sources/status", response_model=SourceStatus)
def get_source_status(record_id: int) -> SourceStatus:
    try:
        return SourceStatus(retained=get_repository().get_source_status(record_id))
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.delete("/{record_id}/sources", status_code=status.HTTP_204_NO_CONTENT)
def delete_application_sources(record_id: int) -> Response:
    try:
        get_repository().delete_sources(record_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{record_id}/draft", response_model=ApplicationDraft)
def get_application_draft(record_id: int, template: DraftTemplate = "standard") -> ApplicationDraft:
    return compose_draft(get_application(record_id), template)


@router.get("/{record_id}/draft/{kind}.{file_format}")
def download_application_draft(
    record_id: int, kind: Literal["resume", "letter"],
    file_format: Literal["docx", "pdf"],
    template: DraftTemplate = "standard",
) -> Response:
    draft = get_application_draft(record_id, template)
    document = draft.resume if kind == "resume" else draft.cover_letter
    return _export_response(document, file_format, f"application-{record_id}-{kind}.{file_format}")


@router.post("/{record_id}/draft-versions", response_model=DraftVersionDetail,
             status_code=status.HTTP_201_CREATED)
def create_draft_version(record_id: int, data: DraftVersionCreate) -> DraftVersionDetail:
    try:
        return get_draft_repository().create(record_id, data)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.get("/{record_id}/draft-versions", response_model=list[DraftVersionSummary])
def list_draft_versions(record_id: int) -> list[DraftVersionSummary]:
    try:
        return get_draft_repository().list(record_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.get("/{record_id}/draft-versions/compare", response_model=VersionComparison)
def compare_draft_versions(
    record_id: int, response: Response,
    from_version: int = Query(ge=1), to_version: int = Query(ge=1),
) -> VersionComparison:
    response.headers["Cache-Control"] = "no-store"
    previous = get_draft_version(record_id, from_version)
    current = get_draft_version(record_id, to_version)
    return compare_versions(record_id, previous, current)


@router.get("/{record_id}/draft-versions/{version}", response_model=DraftVersionDetail)
def get_draft_version(record_id: int, version: Annotated[int, Path(ge=1)]) -> DraftVersionDetail:
    try:
        return get_draft_repository().get(record_id, version)
    except DraftVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="草稿版本不存在。") from exc


@router.patch("/{record_id}/draft-versions/{version}/review",
              response_model=DraftVersionDetail)
def review_draft_version(record_id: int, version: Annotated[int, Path(ge=1)],
                         data: DraftReviewRequest) -> DraftVersionDetail:
    try:
        return get_draft_repository().confirm(record_id, version)
    except DraftVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="草稿版本不存在。") from exc


@router.get("/{record_id}/draft-versions/{version}/evidence", response_model=EvidenceReport)
def get_version_evidence(
    record_id: int, version: Annotated[int, Path(ge=1)], response: Response,
) -> EvidenceReport:
    response.headers["Cache-Control"] = "no-store"
    saved = get_draft_version(record_id, version)
    sources = get_repository().get_sources(record_id)
    if sources is None:
        raise HTTPException(status_code=409, detail="此投递未授权留存原文，无法进行字面证据检查。")
    annotations = get_annotation_repository().list_for_version(saved.id)
    return check_version_evidence(record_id, saved, *sources, annotations)


@router.put("/{record_id}/draft-versions/{version}/annotations",
            response_model=AnnotationDetail)
def upsert_version_annotation(
    record_id: int, version: Annotated[int, Path(ge=1)],
    data: AnnotationWrite, response: Response,
) -> AnnotationDetail:
    response.headers["Cache-Control"] = "no-store"
    saved = get_draft_version(record_id, version)
    document = saved.resume if data.document == "resume" else saved.cover_letter
    if (data.section_index >= len(document.sections) or
            data.line_index >= len(document.sections[data.section_index].lines)):
        raise HTTPException(status_code=422, detail="标注位置不属于该草稿版本。")
    sources = get_repository().get_sources(record_id)
    if sources is None:
        raise HTTPException(status_code=409, detail="此投递未留存原文，无法关联人工证据。")
    source_text = sources[0] if data.source_kind == "resume" else sources[1]
    if not literal_in_source(data.source_quote, source_text):
        raise HTTPException(status_code=422, detail="引用片段未在所选来源原文中找到。")
    try:
        return get_annotation_repository().upsert(record_id, saved.id, data)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="原文已被删除或标注状态已变化，请刷新重试。") from exc


@router.delete("/{record_id}/draft-versions/{version}/annotations",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_version_annotation(
    record_id: int, version: Annotated[int, Path(ge=1)],
    document: DocumentKind, section_index: int = Query(ge=0),
    line_index: int = Query(ge=0),
) -> Response:
    saved = get_draft_version(record_id, version)
    get_annotation_repository().delete(saved.id, document, section_index, line_index)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{record_id}/draft-versions/{version}/{kind}.{file_format}")
def download_draft_version(
    record_id: int, version: Annotated[int, Path(ge=1)],
    kind: Literal["resume", "letter"], file_format: Literal["docx", "pdf"],
) -> Response:
    saved = get_draft_version(record_id, version)
    if saved.reviewed_at is None:
        raise HTTPException(status_code=409, detail="请先核对并确认该版本，再下载。")
    document = saved.resume if kind == "resume" else saved.cover_letter
    filename = f"application-{record_id}-v{version}-{kind}.{file_format}"
    return _export_response(document, file_format, filename)


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
