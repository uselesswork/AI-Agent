from typing import Literal

from pydantic import ValidationError

from app.core.config import get_settings
from app.models.job import JobProfile
from app.prompts.job_analysis import SYSTEM_PROMPT, build_job_analysis_prompt
from app.services.llm import JSONGenerator, LLMResponseError, OpenAICompatibleClient


class JobAnalyzer:
    def __init__(self, generator: JSONGenerator) -> None:
        self.generator = generator

    @property
    def provider(self) -> str:
        return self.generator.provider

    @property
    def model(self) -> str:
        return self.generator.model

    async def analyze(self, description: str) -> JobProfile:
        data = await self.generator.generate_json(SYSTEM_PROMPT, build_job_analysis_prompt(description))
        try:
            return JobProfile.model_validate(data)
        except ValidationError as exc:
            raise LLMResponseError("大模型返回的数据不符合岗位画像结构，请重试。") from exc


def build_job_analyzer(provider: Literal["openai", "deepseek"] | None = None) -> JobAnalyzer:
    return JobAnalyzer(OpenAICompatibleClient(get_settings().provider_config(provider)))
