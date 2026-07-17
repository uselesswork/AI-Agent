from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parents[2]


class LLMConfigurationError(RuntimeError):
    """大模型环境变量缺失或无效。"""


@dataclass(frozen=True)
class ProviderConfig:
    provider: Literal["openai", "deepseek"]
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float
    max_retries: int
    max_output_tokens: int


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: Literal["openai", "deepseek"] = "openai"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    openai_base_url: str = "https://api.openai.com/v1"
    deepseek_api_key: SecretStr | None = None
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_timeout_seconds: float = 60
    llm_max_retries: int = 2
    llm_max_output_tokens: int = 4096

    def provider_config(
        self, provider: Literal["openai", "deepseek"] | None = None
    ) -> ProviderConfig:
        selected_provider = provider or self.llm_provider
        if selected_provider == "openai":
            api_key = self.openai_api_key
            model = self.openai_model
            base_url = self.openai_base_url
        else:
            api_key = self.deepseek_api_key
            model = self.deepseek_model
            base_url = self.deepseek_base_url

        if api_key is None or not api_key.get_secret_value().strip():
            variable = (
                "OPENAI_API_KEY" if selected_provider == "openai" else "DEEPSEEK_API_KEY"
            )
            raise LLMConfigurationError(f"未配置 {variable}，无法生成候选人画像。")
        if not model.strip():
            raise LLMConfigurationError("模型名称不能为空。")
        if self.llm_timeout_seconds <= 0:
            raise LLMConfigurationError("LLM_TIMEOUT_SECONDS 必须大于 0。")
        if self.llm_max_retries < 0:
            raise LLMConfigurationError("LLM_MAX_RETRIES 不能小于 0。")
        if self.llm_max_output_tokens <= 0:
            raise LLMConfigurationError("LLM_MAX_OUTPUT_TOKENS 必须大于 0。")

        return ProviderConfig(
            provider=selected_provider,
            api_key=api_key.get_secret_value(),
            model=model.strip(),
            base_url=base_url.rstrip("/"),
            timeout_seconds=self.llm_timeout_seconds,
            max_retries=self.llm_max_retries,
            max_output_tokens=self.llm_max_output_tokens,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
