from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator, model_validator

from app.validation import normalize_http_url

Language = Literal["中文", "英文", "中英混合"]
PlanStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=40)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PlanCreate(BaseModel):
    topic: str = Field(min_length=2, max_length=120)
    goal: str = Field(min_length=10, max_length=1500)
    level: Literal["零基础", "入门", "进阶", "项目实战"]
    weekly_hours: int = Field(ge=1, le=40)
    duration_weeks: int = Field(ge=1, le=52)
    language: Language = "中文"
    constraints: str = Field(default="", max_length=1000)

    @field_validator("topic", "goal", "constraints")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    topic: str
    goal: str
    level: str
    weekly_hours: int
    duration_weeks: int
    language: Language
    constraints: str
    status: PlanStatus
    stage: str
    progress: int = Field(ge=0, le=100)
    error: str | None
    roadmap: dict | None
    resources: list | None
    evaluation: dict | None
    model_name: str | None
    cost_usd: float | None
    token_usage: dict | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @field_validator("created_at", "updated_at", "started_at", "completed_at", mode="before")
    @classmethod
    def attach_utc(cls, value: datetime | None) -> datetime | None:
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class CredentialsUpdate(BaseModel):
    tavily_api_key: str = ""
    llm_api_key: str = ""
    llm_model: str = Field(default="openai/gpt-4o-mini", min_length=3, max_length=200)
    llm_base_url: str = ""
    clear_tavily_api_key: bool = False
    clear_llm_api_key: bool = False

    @field_validator("tavily_api_key", "llm_api_key")
    @classmethod
    def strip_keys(cls, value: str) -> str:
        return value.strip()

    @field_validator("llm_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return normalize_http_url(value, "模型接口地址")

    @model_validator(mode="after")
    def validate_clear_flags(self):
        conflicts = []
        if self.clear_tavily_api_key and self.tavily_api_key:
            conflicts.append("Tavily API Key")
        if self.clear_llm_api_key and self.llm_api_key:
            conflicts.append("大模型 API Key")
        if conflicts:
            raise ValueError(f"不能同时填写并清除：{'、'.join(conflicts)}")
        return self


class CredentialsStatus(BaseModel):
    configured: bool
    tavily_configured: bool
    llm_configured: bool
    llm_model: str
    llm_base_url: str


class Source(BaseModel):
    id: str
    title: str
    url: HttpUrl
    snippet: str
    provider: str = ""
    score: float = 0
    resource_type: str = "文档"


class ScheduleItem(BaseModel):
    period: str
    focus: str
    output: str


class Stage(BaseModel):
    name: str
    weeks: int = Field(ge=1)
    focus: str
    topics: list[str]
    practice: str
    deliverable: str
    resource_ids: list[str]
    objectives: list[str] = Field(default_factory=list)
    schedule: list[ScheduleItem] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class Roadmap(BaseModel):
    title: str
    overview: str
    prerequisites: list[str]
    stages: list[Stage]
    learning_outcomes: list[str]
    final_project: str
    study_strategy: list[str] = Field(default_factory=list)
    project_requirements: list[str] = Field(default_factory=list)


class EvaluationDimension(BaseModel):
    name: str
    score: int = Field(ge=0, le=20)
    comment: str


class PlanEvaluation(BaseModel):
    total_score: int = Field(ge=0, le=100)
    verdict: Literal["recommended", "needs_revision"]
    summary: str
    strengths: list[str]
    issues: list[str]
    recommendations: list[str]
    dimensions: list[EvaluationDimension]
