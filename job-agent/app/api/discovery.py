"""用户指定公开招聘板后的职位预览、筛选和显式导入。"""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.applications import get_repository
from app.api.library import get_library_repository
from app.core.config import LLMConfigurationError
from app.models.discovery import (
    DiscoveryResults, DiscoverySearch, ImportRecord, ImportRequest, ImportResult,
    PostingPreview,
)
from app.models.library import JobAssetCreate
from app.services.discovery_repository import DiscoveryRepository
from app.services.job_analyzer import build_job_analyzer
from app.services.job_discovery import (
    DiscoveryServiceError, PostingNotFoundError, filter_postings,
    get_posting, list_postings,
)
from app.services.llm import LLMServiceError

router = APIRouter(prefix="/api/discovery", tags=["岗位发现"])


def get_discovery_repository() -> DiscoveryRepository:
    return DiscoveryRepository(get_repository().engine)


@router.post("/search", response_model=DiscoveryResults)
def search_postings(query: DiscoverySearch) -> DiscoveryResults:
    try:
        postings, source_truncated = list_postings(query.source, query.board_token)
    except PostingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DiscoveryServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    filtered = filter_postings(postings, query)
    imported = get_discovery_repository().imported_ids(query.source, query.board_token)
    return DiscoveryResults(
        items=[PostingPreview(
            source=item.source, board_token=item.board_token,
            external_id=item.external_id, title=item.title, company=item.company,
            location=item.location, commitment=item.commitment, job_url=item.job_url,
            description_excerpt=item.description[:500],
            imported_job_id=imported.get(item.external_id),
        ) for item in filtered[:100]],
        scanned=len(postings), truncated=source_truncated or len(filtered) > 100,
    )


@router.get("/imports", response_model=list[ImportRecord])
def list_imports() -> list[ImportRecord]:
    return get_discovery_repository().list()


@router.post("/imports", response_model=ImportResult)
async def import_posting(request: ImportRequest) -> ImportResult:
    repository = get_discovery_repository()
    existing = repository.get(request.source, request.board_token, request.external_id)
    if existing is not None:
        return ImportResult(record=existing, created=False, job_reused=True)
    try:
        posting = await run_in_threadpool(
            get_posting, request.source, request.board_token, request.external_id,
        )
    except PostingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DiscoveryServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if len(posting.description.strip()) < 20:
        raise HTTPException(status_code=422, detail="该职位没有足够的岗位描述，无法结构化导入。")
    try:
        analyzer = build_job_analyzer(request.llm_provider)
        profile = await analyzer.analyze(posting.description)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # 标题、公司和地点由公开职位接口给出，只补模型未识别的字段。
    profile = profile.model_copy(update={
        "title": profile.title or posting.title,
        "company": profile.company or posting.company,
        "location": profile.location or posting.location,
    })
    try:
        saved = get_library_repository().save_job(JobAssetCreate(
            profile=profile, job_url=posting.job_url,
        ))
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="职位来源链接或画像无效，未导入。") from exc
    record, created = repository.create(
        request.source, request.board_token, request.external_id,
        saved.asset.id, posting.job_url,
    )
    return ImportResult(record=record, created=created, job_reused=not saved.created)
