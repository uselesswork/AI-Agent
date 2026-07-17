from pydantic import ValidationError

from app.core.config import get_settings
from app.models.candidate import CandidateProfile
from app.prompts.resume_analysis import SYSTEM_PROMPT, build_resume_analysis_prompt
from app.services.llm import JSONGenerator, LLMResponseError, OpenAICompatibleClient


class ResumeAnalyzer:
    def __init__(self, generator: JSONGenerator) -> None:
        self.generator = generator

    @property
    def provider(self) -> str:
        return self.generator.provider

    @property
    def model(self) -> str:
        return self.generator.model

    async def analyze(self, resume_text: str) -> CandidateProfile:
        data = await self.generator.generate_json(
            SYSTEM_PROMPT,
            build_resume_analysis_prompt(resume_text),
        )
        try:
            return CandidateProfile.model_validate(data)
        except ValidationError as exc:
            raise LLMResponseError("大模型返回的数据不符合候选人画像结构，请重试。") from exc


def build_resume_analyzer() -> ResumeAnalyzer:
    config = get_settings().provider_config()
    return ResumeAnalyzer(OpenAICompatibleClient(config))
