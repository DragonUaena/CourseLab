from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    plans: Mapped[list["LearningPlan"]] = relationship(cascade="all, delete-orphan")


class UserCredential(Base):
    __tablename__ = "user_credentials"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    encrypted_payload: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(30))
    weekly_hours: Mapped[int] = mapped_column(Integer)
    duration_weeks: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(30), default="中文")
    constraints: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(80), default="等待生成")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    roadmap: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
