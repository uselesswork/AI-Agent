from typing import Literal

from pydantic import ValidationError

from app.core.config import get_settings
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchResult
from app.prompts.match_analysis import SYSTEM_PROMPT, build_match_analysis_prompt
from app.services.llm import JSONGenerator, LLMResponseError, OpenAICompatibleClient


class MatchAnalyzer:
    def __init__(self, generator: JSONGenerator) -> None:
        self.generator = generator

    @property
    def provider(self) -> str:
        return self.generator.provider

    @property
    def model(self) -> str:
        return self.generator.model

    async def analyze(self, candidate: CandidateProfile, job: JobProfile) -> MatchResult:
        data = await self.generator.generate_json(
            SYSTEM_PROMPT, build_match_analysis_prompt(candidate, job)
        )
        try:
            return MatchResult.model_validate(data)
        except ValidationError as exc:
            raise LLMResponseError("大模型返回的数据不符合匹配结果结构，请重试。") from exc


def build_match_analyzer(
    provider: Literal["openai", "deepseek"] | None = None,
) -> MatchAnalyzer:
    return MatchAnalyzer(OpenAICompatibleClient(get_settings().provider_config(provider)))
