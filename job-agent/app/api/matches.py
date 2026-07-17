from fastapi import APIRouter, HTTPException, status

from app.core.config import LLMConfigurationError
from app.models.match import MatchAnalyzeRequest, MatchAnalyzeResponse
from app.services.llm import LLMServiceError
from app.services.match_analyzer import build_match_analyzer

router = APIRouter(prefix="/api/matches", tags=["匹配"])


@router.post("/analyze", response_model=MatchAnalyzeResponse)
async def analyze_match(request: MatchAnalyzeRequest) -> MatchAnalyzeResponse:
    try:
        analyzer = build_match_analyzer(request.provider)
        result = await analyzer.analyze(request.candidate_profile, request.job_profile)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return MatchAnalyzeResponse(provider=analyzer.provider, model=analyzer.model, result=result)
