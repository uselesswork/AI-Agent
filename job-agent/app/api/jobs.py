from fastapi import APIRouter, HTTPException, status

from app.core.config import LLMConfigurationError
from app.models.job import JobParseRequest, JobParseResponse
from app.services.job_analyzer import build_job_analyzer
from app.services.llm import LLMServiceError

router = APIRouter(prefix="/api/jobs", tags=["岗位"])


@router.post("/parse", response_model=JobParseResponse)
async def parse_job(request: JobParseRequest) -> JobParseResponse:
    try:
        analyzer = build_job_analyzer(request.provider)
        profile = await analyzer.analyze(request.description)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return JobParseResponse(provider=analyzer.provider, model=analyzer.model, profile=profile)
