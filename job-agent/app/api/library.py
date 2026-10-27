"""独立资料库与报告历史；重新分析会调用所选大模型。"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from app.api.applications import get_repository
from app.core.config import LLMConfigurationError
from app.models.library import (
    FavoriteUpdate, JobAsset, JobAssetCreate, JobAssetSaved, MatchReanalyzeRequest,
    ReportDetail, ReportSummary, ResumeAsset, ResumeAssetCreate, ResumeAssetSaved,
)
from app.services.library_repository import (
    AssetInUseError, AssetNotFoundError, LibraryRepository,
)
from app.services.llm import LLMServiceError
from app.services.match_analyzer import build_match_analyzer

router = APIRouter(prefix="/api/library", tags=["资料库"])


def get_library_repository() -> LibraryRepository:
    return LibraryRepository(get_repository().engine)


@router.post("/resumes", response_model=ResumeAssetSaved)
def save_resume(data: ResumeAssetCreate) -> ResumeAssetSaved:
    return get_library_repository().save_resume(data)


@router.get("/resumes", response_model=list[ResumeAsset])
def list_resumes() -> list[ResumeAsset]:
    return get_library_repository().list_resumes()


@router.get("/resumes/{record_id}", response_model=ResumeAsset)
def get_resume(record_id: Annotated[int, Path(ge=1)]) -> ResumeAsset:
    try:
        return get_library_repository().get_resume(record_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="简历画像不存在。") from exc


@router.delete("/resumes/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(record_id: Annotated[int, Path(ge=1)]) -> Response:
    try:
        get_library_repository().delete_resume(record_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="简历画像不存在。") from exc
    except AssetInUseError as exc:
        raise HTTPException(status_code=409, detail="简历仍被报告或投递引用，不能删除。") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/jobs", response_model=JobAssetSaved)
def save_job(data: JobAssetCreate) -> JobAssetSaved:
    return get_library_repository().save_job(data)


@router.get("/jobs", response_model=list[JobAsset])
def list_jobs(favorite_only: bool = False) -> list[JobAsset]:
    return get_library_repository().list_jobs(favorite_only)


@router.get("/jobs/{record_id}", response_model=JobAsset)
def get_job(record_id: Annotated[int, Path(ge=1)]) -> JobAsset:
    try:
        return get_library_repository().get_job(record_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="岗位资料不存在。") from exc


@router.patch("/jobs/{record_id}/favorite", response_model=JobAsset)
def set_favorite(record_id: Annotated[int, Path(ge=1)], data: FavoriteUpdate) -> JobAsset:
    try:
        return get_library_repository().set_favorite(record_id, data.favorite)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="岗位资料不存在。") from exc


@router.delete("/jobs/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(record_id: Annotated[int, Path(ge=1)]) -> Response:
    try:
        get_library_repository().delete_job(record_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="岗位资料不存在。") from exc
    except AssetInUseError as exc:
        raise HTTPException(status_code=409, detail="岗位仍被报告或投递引用，不能删除。") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reports", response_model=list[ReportSummary])
def list_reports(
    resume_id: int | None = Query(default=None, ge=1),
    job_id: int | None = Query(default=None, ge=1),
) -> list[ReportSummary]:
    return get_library_repository().list_reports(resume_id, job_id)


@router.post("/reports/reanalyze", response_model=ReportDetail,
             status_code=status.HTTP_201_CREATED)
async def reanalyze_report(request: MatchReanalyzeRequest) -> ReportDetail:
    repository = get_library_repository()
    try:
        resume = repository.get_resume(request.resume_id)
        job = repository.get_job(request.job_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="所选简历或岗位不存在。") from exc
    try:
        analyzer = build_match_analyzer(request.provider)
        result = await analyzer.analyze(resume.profile, job.profile)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        return repository.save_report(request.resume_id, request.job_id, result,
                                      analyzer.provider, analyzer.model)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=409, detail="分析期间资料被删除，请重新选择。") from exc


@router.get("/reports/{record_id}", response_model=ReportDetail)
def get_report(record_id: Annotated[int, Path(ge=1)]) -> ReportDetail:
    try:
        return get_library_repository().get_report(record_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="匹配报告不存在。") from exc
