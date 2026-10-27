from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


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
    language: str = Field(default="中文", max_length=30)
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
    language: str
    constraints: str
    status: str
    stage: str
    progress: int
    error: str | None
    roadmap: dict | None
    resources: list | None
    evaluation: dict | None
    model_name: str | None
    cost_usd: float | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class CredentialsUpdate(BaseModel):
    tavily_api_key: str = ""
    llm_api_key: str = ""
    llm_model: str = Field(default="openai/gpt-4o-mini", min_length=3, max_length=200)
    llm_base_url: str = ""


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


class Stage(BaseModel):
    name: str
    weeks: int = Field(ge=1)
    focus: str
    topics: list[str]
    practice: str
    deliverable: str
    resource_ids: list[str]


class Roadmap(BaseModel):
    title: str
    overview: str
    prerequisites: list[str]
    stages: list[Stage]
    learning_outcomes: list[str]
    final_project: str


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
