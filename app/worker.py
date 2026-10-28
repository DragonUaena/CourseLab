import logging
import queue
import re
import threading
import time
from datetime import UTC, datetime

from sqlalchemy import select

from app.config import PROJECT_ROOT, Settings
from app.course_crew import CourseCrew, GenerationCancelled, audit_plan
from app.credentials import CredentialCipher, InvalidCredentialsError, MissingCredentialsError, resolve_credentials
from app.database import Database
from app.models import LearningPlan, utcnow
from app.report import render_report
from app.research import TavilyResearcher

logger = logging.getLogger(__name__)


def format_generation_error(exc: Exception) -> str:
    message = str(exc)
    if "length limit was reached" not in message.lower():
        return f"生成失败：{message[:500]}"
    completion_match = re.search(r"completion_tokens=(\d+)", message)
    reasoning_match = re.search(r"reasoning_tokens=(\d+)", message)
    completion_tokens = completion_match.group(1) if completion_match else "上限"
    reasoning_tokens = reasoning_match.group(1) if reasoning_match else "未知"
    return (
        f"生成失败：模型在输出正文前用尽了 {completion_tokens} tokens 的推理额度"
        f"（reasoning={reasoning_tokens}）。当前详细报告需要推理和结构化输出两部分空间；"
        "请将 COURSELAB_LLM_MAX_TOKENS 调高到至少 12000、降低 "
        "COURSELAB_LLM_REASONING_EFFORT，或改用非推理模型后重试。"
    )


class CourseLabQueue:
    def __init__(self, database: Database, settings: Settings, cipher: CredentialCipher) -> None:
        self.database = database
        self.settings = settings
        self.cipher = cipher
        self.items: queue.Queue[str | None] = queue.Queue()
        self.thread = threading.Thread(target=self._run, name="courselab-worker", daemon=True)

    def start(self) -> None:
        self.recover_interrupted()
        self.thread.start()

    def recover_interrupted(self) -> None:
        with self.database.sessions() as session:
            interrupted = list(session.scalars(select(LearningPlan).where(LearningPlan.status == "running")))
            for plan in interrupted:
                plan.status = "failed"
                plan.stage = "生成中断"
                plan.progress = 100
                plan.error = "服务重启导致生成中断，请重新生成这份计划"
                plan.updated_at = utcnow()
                plan.completed_at = utcnow()
            queued_ids = list(
                session.scalars(
                    select(LearningPlan.id).where(LearningPlan.status == "queued").order_by(LearningPlan.created_at)
                )
            )
            session.commit()
        if interrupted:
            logger.warning("Marked %s interrupted plans as failed", len(interrupted))
        for plan_id in queued_ids:
            self.enqueue(plan_id)

    def stop(self) -> None:
        self.items.put(None)
        self.thread.join(timeout=5)

    def enqueue(self, plan_id: str) -> None:
        self.items.put(plan_id)

    def _run(self) -> None:
        while plan_id := self.items.get():
            try:
                self._generate(plan_id)
            except Exception:
                logger.exception("CourseLab worker failed for plan %s", plan_id)
            finally:
                self.items.task_done()

    def _generate(self, plan_id: str) -> None:
        with self.database.sessions() as session:
            plan = session.get(LearningPlan, plan_id)
            if plan is None:
                return
            try:
                if plan.status != "queued":
                    return
                credentials = resolve_credentials(session, self.settings, self.cipher, plan.user_id)
                plan.status = "running"
                plan.stage = "Tavily 正在检索资料"
                plan.progress = 12
                plan.started_at = utcnow()
                generation_started = time.monotonic()
                session.commit()
                profile = {
                    "topic": plan.topic,
                    "goal": plan.goal,
                    "level": plan.level,
                    "weekly_hours": plan.weekly_hours,
                    "duration_weeks": plan.duration_weeks,
                    "language": plan.language,
                    "constraints": plan.constraints,
                }
                sources = TavilyResearcher(
                    credentials.tavily_api_key,
                    results_per_query=self.settings.tavily_results_per_query,
                    max_sources=self.settings.tavily_max_sources,
                ).search(plan.topic, plan.goal, plan.language)
                if self._cancelled(session, plan):
                    return
                plan.stage = f"已检索 {len(sources)} 个来源，CrewAI 正在编排路线"
                plan.progress = 38
                session.commit()
                crew_result = CourseCrew(
                    credentials,
                    max_tokens=self.settings.llm_max_tokens,
                    prompt_source_chars=self.settings.prompt_source_chars,
                    reasoning_effort=self.settings.llm_reasoning_effort,
                    cancel_check=lambda: self._cancelled_in_database(plan_id),
                ).generate(profile, sources)
                if self._cancelled(session, plan):
                    return
                plan.stage = "独立 Agent 正在审查计划可用性"
                plan.progress = 82
                session.commit()
                audit = audit_plan(profile, crew_result.roadmap, crew_result.resources)
                evaluation = CourseCrew.blend_evaluation(crew_result.evaluation, audit)
                if self._cancelled(session, plan):
                    return
                plan.roadmap = crew_result.roadmap
                plan.resources = crew_result.resources
                plan.evaluation = evaluation
                plan.model_name = credentials.llm_model
                plan.token_usage = crew_result.token_usage
                completed_at = datetime.now(UTC)
                generation_seconds = round(time.monotonic() - generation_started, 1)
                plan.report_markdown = render_report(
                    profile,
                    crew_result.roadmap,
                    crew_result.resources,
                    evaluation,
                    generation_seconds=generation_seconds,
                    token_usage=crew_result.token_usage,
                )
                plan.status = "completed"
                plan.stage = "计划生成完成"
                plan.progress = 100
                plan.completed_at = completed_at
                session.commit()
            except GenerationCancelled:
                return
            except (InvalidCredentialsError, MissingCredentialsError) as exc:
                self._fail(session, plan, str(exc))
            except Exception as exc:
                logger.exception("CourseLab generation failed for plan %s", plan_id)
                self._fail(session, plan, format_generation_error(exc))

    def _cancelled_in_database(self, plan_id: str) -> bool:
        with self.database.sessions() as session:
            status = session.scalar(select(LearningPlan.status).where(LearningPlan.id == plan_id))
        return status == "cancelled"

    @staticmethod
    def _cancelled(session, plan: LearningPlan) -> bool:
        session.refresh(plan)
        return plan.status == "cancelled"

    @staticmethod
    def _fail(session, plan: LearningPlan, message: str) -> None:
        session.refresh(plan)
        if plan.status == "cancelled":
            return
        plan.status = "failed"
        plan.stage = "生成中断"
        plan.error = message
        plan.progress = 100
        plan.updated_at = utcnow()
        plan.completed_at = utcnow()
        session.commit()


def build_cipher(settings: Settings) -> CredentialCipher:
    return CredentialCipher(settings.credential_key, PROJECT_ROOT / "data" / ".credential_key")
