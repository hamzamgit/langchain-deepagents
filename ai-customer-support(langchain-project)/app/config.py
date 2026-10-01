"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings for the AI Customer Support Agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Customer Support Agent"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/support.db",
        description="Async SQLAlchemy database URL",
    )

    llm_api_key: str = Field(default="", description="LLM provider API key")
    llm_model: str = Field(default="openai/gpt-4o-mini")
    llm_base_url: str | None = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenAI-compatible base URL (e.g. OpenRouter)",
    )
    llm_temperature: float = 0.0

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "ai-customer-support"
    langchain_tracing_v2: bool = False

    # Bumped when agent behavior/prompts change — shows up on every LangSmith trace
    agent_version: str = Field(default="v1", description="Support agent version tag for traces/evals")

    checkpoint_db_path: str = "./data/checkpoints.db"
    knowledge_dir: str = "./knowledge"

    # pydantic-settings maps KNOWLEDGE_DIR automatically via field name

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def tracing_enabled(self) -> bool:
        return bool(self.langsmith_tracing or self.langchain_tracing_v2) and bool(
            self.langsmith_api_key
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
