import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import hash_password
from app.config import Settings
from app.course_crew import CourseCrew, CrewResult
from app.database import Database
from app.demo_data import DEMO_EVALUATION, DEMO_RESOURCES, DEMO_ROADMAP
from app.main import create_app
from app.models import LearningPlan, User


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_startup_recovers_queued_and_interrupted_plans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_url = f"sqlite:///{(tmp_path / 'restart.db').as_posix()}"
    database = Database(database_url)
    database.create_all()
    with database.sessions() as session:
        user = User(
            email="restart@example.com",
            display_name="Restart",
            password_hash=hash_password("correct-password"),
        )
        session.add(user)
        session.flush()
        queued = LearningPlan(
            user_id=user.id,
            topic="FastAPI 重启恢复",
            goal="验证服务重启后的排队任务能够继续生成",
            level="入门",
            weekly_hours=6,
            duration_weeks=6,
            language="中文",
            status="queued",
        )
        interrupted = LearningPlan(
            user_id=user.id,
            topic="FastAPI 中断恢复",
            goal="验证服务重启后的运行任务会结束为可重试状态",
            level="入门",
            weekly_hours=6,
            duration_weeks=6,
            language="中文",
            status="running",
            stage="CrewAI 正在编排路线",
            progress=38,
        )
        session.add_all([queued, interrupted])
        session.commit()
        queued_id = queued.id
        interrupted_id = interrupted.id
    database.close()

    class FakeResearcher:
        def __init__(self, _api_key: str, **_kwargs):
            pass

        def search(self, _topic: str, _goal: str, _language: str):
            return DEMO_RESOURCES

    class FakeCrew:
        def __init__(self, _credentials, **_kwargs):
            pass

        def generate(self, _profile, _sources):
            return CrewResult(
                roadmap=DEMO_ROADMAP,
                resources=DEMO_RESOURCES,
                evaluation=DEMO_EVALUATION,
                token_usage={
                    "prompt_tokens": 1200,
                    "completion_tokens": 800,
                    "total_tokens": 2000,
                },
            )

        blend_evaluation = staticmethod(CourseCrew.blend_evaluation)

    monkeypatch.setattr("app.worker.TavilyResearcher", FakeResearcher)
    monkeypatch.setattr("app.worker.CourseCrew", FakeCrew)
    settings = Settings(
        database_url=database_url,
        secret_key="restart-test-secret-with-at-least-32-bytes",
        credential_key="restart-test-credential-key",
        tavily_api_key="tvly-test",
        openai_api_key="sk-test",
    )

    with TestClient(create_app(settings)) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": "restart@example.com", "password": "correct-password"},
        )
        headers = auth_headers(login.json()["access_token"])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            queued_response = client.get(f"/api/plans/{queued_id}", headers=headers)
            if queued_response.json()["status"] == "completed":
                break
            time.sleep(0.05)
        else:
            pytest.fail("重启后的排队计划没有完成")

        interrupted_response = client.get(f"/api/plans/{interrupted_id}", headers=headers)
        assert interrupted_response.json()["status"] == "failed"
        assert "服务重启" in interrupted_response.json()["error"]
        report = client.get(f"/api/plans/{queued_id}/report", headers=headers)
        assert report.status_code == 200
        assert "FastAPI 六周项目路线" in report.text
        assert "生成耗时" in report.text
        assert "2,000 tokens" in report.text
        completed = queued_response.json()
        assert completed["started_at"] is not None
        assert completed["completed_at"] is not None
        assert completed["token_usage"]["total_tokens"] == 2000


@pytest.mark.parametrize("failure_stage", ["search", "crew"])
def test_generation_errors_mark_plan_failed(
    client: TestClient,
    registered_user: dict,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
):
    headers = auth_headers(registered_user["access_token"])
    assert (
        client.put(
            "/api/settings/credentials",
            headers=headers,
            json={
                "tavily_api_key": "tvly-test",
                "llm_api_key": "sk-test",
                "llm_model": "openai/gpt-4o-mini",
                "llm_base_url": "",
            },
        ).status_code
        == 200
    )
    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=registered_user["user"]["id"],
            topic="故意失败的任务",
            goal="验证后台生成失败时会进入可重试状态",
            level="入门",
            weekly_hours=4,
            duration_weeks=4,
            language="中文",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    class Researcher:
        def __init__(self, _api_key: str, **_kwargs):
            pass

        def search(self, _topic: str, _goal: str, _language: str):
            if failure_stage == "search":
                raise RuntimeError("Tavily 没有返回可用资料")
            return DEMO_RESOURCES

    class BrokenCrew:
        def __init__(self, _credentials, **_kwargs):
            pass

        def generate(self, _profile, _sources):
            raise RuntimeError("模型服务不可用")

    monkeypatch.setattr("app.worker.TavilyResearcher", Researcher)
    monkeypatch.setattr("app.worker.CourseCrew", BrokenCrew)
    client.app.state.worker._generate(plan_id)

    with client.app.state.database.sessions() as session:
        failed = session.scalar(select(LearningPlan).where(LearningPlan.id == plan_id))
        assert failed.status == "failed"
        assert failed.progress == 100
        assert failed.error
        assert "生成失败" in failed.error


def test_stop_takes_effect_at_the_next_worker_boundary(
    client: TestClient,
    registered_user: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    headers = auth_headers(registered_user["access_token"])
    client.put(
        "/api/settings/credentials",
        headers=headers,
        json={
            "tavily_api_key": "tvly-test",
            "llm_api_key": "sk-test",
            "llm_model": "openai/gpt-4o-mini",
            "llm_base_url": "",
        },
    )
    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=registered_user["user"]["id"],
            topic="停止边界测试",
            goal="确认用户在检索后停止任务时不会继续调用模型",
            level="入门",
            weekly_hours=4,
            duration_weeks=4,
            language="中文",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    crew_called = False

    class CancellingResearcher:
        def __init__(self, _api_key: str, **_kwargs):
            pass

        def search(self, _topic: str, _goal: str, _language: str):
            with client.app.state.database.sessions() as session:
                current = session.get(LearningPlan, plan_id)
                current.status = "cancelled"
                current.stage = "已停止生成"
                session.commit()
            return DEMO_RESOURCES

    class UnexpectedCrew:
        def __init__(self, _credentials, **_kwargs):
            nonlocal crew_called
            crew_called = True

    monkeypatch.setattr("app.worker.TavilyResearcher", CancellingResearcher)
    monkeypatch.setattr("app.worker.CourseCrew", UnexpectedCrew)
    client.app.state.worker._generate(plan_id)

    with client.app.state.database.sessions() as session:
        stopped = session.get(LearningPlan, plan_id)
        assert stopped.status == "cancelled"
        assert stopped.roadmap is None
    assert crew_called is False
