import pytest

from app.core.config import LLMConfigurationError, Settings


def test_openai_provider_config() -> None:
    config = Settings(
        _env_file=None,
        llm_provider="openai",
        openai_api_key="sk-test",
        openai_model="gpt-test",
    ).provider_config()

    assert config.provider == "openai"
    assert config.api_key == "sk-test"
    assert config.model == "gpt-test"
    assert config.base_url == "https://api.openai.com/v1"


def test_deepseek_provider_config() -> None:
    config = Settings(
        _env_file=None,
        llm_provider="deepseek",
        deepseek_api_key="ds-test",
    ).provider_config()

    assert config.provider == "deepseek"
    assert config.api_key == "ds-test"
    assert config.model == "deepseek-v4-flash"
    assert config.base_url == "https://api.deepseek.com"


def test_selected_provider_requires_api_key() -> None:
    settings = Settings(_env_file=None, llm_provider="deepseek", deepseek_api_key=None)

    with pytest.raises(LLMConfigurationError, match="DEEPSEEK_API_KEY"):
        settings.provider_config()


def test_mysql_database_url_is_required() -> None:
    settings = Settings(
        _env_file=None,
        database_url="mysql+pymysql://user:password@127.0.0.1:3306/job_agent",
    )
    assert settings.validated_database_url().startswith("mysql+pymysql://")

    invalid = Settings(_env_file=None, database_url="sqlite:///./job_agent.db")
    with pytest.raises(LLMConfigurationError):
        invalid.validated_database_url()
