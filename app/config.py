from pathlib import Path
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    secret_key: str = Field(
        "local-development-only-change-me",
        validation_alias=AliasChoices("COURSELAB_SECRET_KEY", "SECRET_KEY", "secret_key"),
    )
    credential_key: str = Field(
        "",
        validation_alias=AliasChoices("COURSELAB_CREDENTIAL_KEY", "credential_key"),
    )
    database_url: str = Field(
        f"sqlite:///{(PROJECT_ROOT / 'data' / 'courselab.db').as_posix()}",
        validation_alias=AliasChoices("COURSELAB_DATABASE_URL", "DATABASE_URL", "database_url"),
    )
    access_token_minutes: int = Field(
        60 * 24 * 7,
        validation_alias=AliasChoices("COURSELAB_ACCESS_TOKEN_MINUTES", "access_token_minutes"),
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        ["http://localhost:5173", "http://127.0.0.1:5173"],
        validation_alias=AliasChoices("COURSELAB_CORS_ORIGINS", "cors_origins"),
    )
    tavily_api_key: str = Field(
        "",
        validation_alias=AliasChoices("TAVILY_API_KEY", "COURSELAB_TAVILY_API_KEY", "tavily_api_key"),
    )
    openai_api_key: str = Field(
        "",
        validation_alias=AliasChoices("OPENAI_API_KEY", "COURSELAB_OPENAI_API_KEY", "openai_api_key"),
    )
    openai_api_base: str = Field(
        "",
        validation_alias=AliasChoices("OPENAI_API_BASE", "COURSELAB_OPENAI_API_BASE", "openai_api_base"),
    )
    llm_model: str = Field(
        "openai/gpt-4o-mini",
        validation_alias=AliasChoices("COURSELAB_LLM_MODEL", "LLM_MODEL", "llm_model"),
    )
    tavily_results_per_query: int = Field(
        4,
        ge=1,
        le=10,
        validation_alias=AliasChoices("COURSELAB_TAVILY_RESULTS_PER_QUERY", "tavily_results_per_query"),
    )
    tavily_max_sources: int = Field(
        12,
        ge=5,
        le=30,
        validation_alias=AliasChoices("COURSELAB_TAVILY_MAX_SOURCES", "tavily_max_sources"),
    )
    prompt_source_chars: int = Field(
        420,
        ge=200,
        le=1400,
        validation_alias=AliasChoices("COURSELAB_PROMPT_SOURCE_CHARS", "prompt_source_chars"),
    )
    llm_max_tokens: int = Field(
        12000,
        ge=2000,
        le=20000,
        validation_alias=AliasChoices("COURSELAB_LLM_MAX_TOKENS", "llm_max_tokens"),
    )
    llm_reasoning_effort: Literal["minimal", "low", "medium", "high"] = Field(
        "low",
        validation_alias=AliasChoices("COURSELAB_LLM_REASONING_EFFORT", "llm_reasoning_effort"),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value
