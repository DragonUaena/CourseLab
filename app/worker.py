import logging
import queue
import threading
from datetime import UTC, datetime

from app.config import PROJECT_ROOT, Settings
from app.course_crew import CourseCrew, audit_plan
from app.credentials import CredentialCipher, MissingCredentialsError, resolve_credentials
from app.database import Database
from app.models import LearningPlan, utcnow
from app.report import render_report
from app.research import TavilyResearcher

logger = logging.getLogger(__name__)


class CourseLabQueue:
    def __init__(self, database: Database, settings: Settings, cipher: CredentialCipher) -> None:
        self.database = database
        self.settings = settings
        self.cipher = cipher
        self.items: queue.Queue[str | None] = queue.Queue()
        self.thread = threading.Thread(target=self._run, name="courselab-worker", daemon=True)

    def start(self) -> None:
        self.thread.start()

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
                credentials = resolve_credentials(session, self.settings, self.cipher, plan.user_id)
                plan.status = "running"
                plan.stage = "Tavily 正在检索资料"
                plan.progress = 12
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
                sources = TavilyResearcher(credentials.tavily_api_key).search(plan.topic, plan.goal, plan.language)
                plan.stage = f"已检索 {len(sources)} 个来源，CrewAI 正在编排路线"
                plan.progress = 38
                session.commit()
                crew_result = CourseCrew(credentials).generate(profile, sources)
                plan.stage = "独立 Agent 正在审查计划可用性"
                plan.progress = 82
                session.commit()
                audit = audit_plan(profile, crew_result.roadmap, crew_result.resources)
                evaluation = CourseCrew.blend_evaluation(crew_result.evaluation, audit)
                plan.roadmap = crew_result.roadmap
                plan.resources = crew_result.resources
                plan.evaluation = evaluation
                plan.model_name = credentials.llm_model
                plan.report_markdown = render_report(profile, crew_result.roadmap, crew_result.resources, evaluation)
                plan.status = "completed"
                plan.stage = "计划生成完成"
                plan.progress = 100
                plan.completed_at = datetime.now(UTC)
                session.commit()
            except MissingCredentialsError as exc:
                self._fail(session, plan, str(exc))
            except Exception as exc:
                logger.exception("CourseLab generation failed for plan %s", plan_id)
                self._fail(session, plan, f"生成失败：{str(exc)[:500]}")

    @staticmethod
    def _fail(session, plan: LearningPlan, message: str) -> None:
        plan.status = "failed"
        plan.stage = "生成中断"
        plan.error = message
        plan.progress = 100
        plan.updated_at = utcnow()
        session.commit()


def build_cipher(settings: Settings) -> CredentialCipher:
    return CredentialCipher(settings.credential_key, PROJECT_ROOT / "data" / ".credential_key")
