from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import LearningPlan, UserCredential


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_accounts_and_learning_plans_are_isolated(client: TestClient):
    alice = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "correct-password", "display_name": "Alice"},
    ).json()
    bob = client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "another-password", "display_name": "Bob"},
    ).json()
    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=alice["user"]["id"],
            topic="Rust 所有权",
            goal="能够写出不依赖克隆的 Rust 数据处理程序",
            level="入门",
            weekly_hours=5,
            duration_weeks=4,
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id
    assert client.get("/api/plans", headers=auth_headers(alice["access_token"])).json()[0]["topic"] == "Rust 所有权"
    assert client.get("/api/plans", headers=auth_headers(bob["access_token"])).json() == []
    assert client.get(f"/api/plans/{plan_id}", headers=auth_headers(bob["access_token"])).status_code == 404


def test_credentials_are_encrypted_and_never_returned(client: TestClient, registered_user: dict):
    headers = auth_headers(registered_user["access_token"])
    response = client.put(
        "/api/settings/credentials",
        headers=headers,
        json={
            "tavily_api_key": "tvly-secret-value",
            "llm_api_key": "sk-secret-value",
            "llm_model": "openai/gpt-4o-mini",
            "llm_base_url": "",
        },
    )
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert "secret-value" not in response.text
    with client.app.state.database.sessions() as session:
        stored = session.scalar(select(UserCredential).where(UserCredential.user_id == registered_user["user"]["id"]))
    assert "tvly-secret-value" not in stored.encrypted_payload
    assert "sk-secret-value" not in stored.encrypted_payload


def test_credentials_can_be_cleared_and_base_url_is_validated(client: TestClient, registered_user: dict):
    headers = auth_headers(registered_user["access_token"])
    saved = client.put(
        "/api/settings/credentials",
        headers=headers,
        json={
            "tavily_api_key": "tvly-secret-value",
            "llm_api_key": "sk-secret-value",
            "llm_model": "openai/gpt-4o-mini",
            "llm_base_url": "",
        },
    )
    assert saved.status_code == 200

    invalid_url = client.put(
        "/api/settings/credentials",
        headers=headers,
        json={
            "llm_model": "openai/gpt-4o-mini",
            "llm_base_url": "not-a-url",
        },
    )
    assert invalid_url.status_code == 422

    cleared = client.put(
        "/api/settings/credentials",
        headers=headers,
        json={
            "llm_model": "openai/gpt-4o-mini",
            "clear_tavily_api_key": True,
            "clear_llm_api_key": True,
        },
    )
    assert cleared.status_code == 200
    assert cleared.json()["configured"] is False


def test_plan_creation_requires_both_api_keys(client: TestClient, registered_user: dict):
    response = client.post(
        "/api/plans",
        headers=auth_headers(registered_user["access_token"]),
        json={
            "topic": "Kubernetes",
            "goal": "能够部署一个带健康检查的 Web 服务",
            "level": "入门",
            "weekly_hours": 4,
            "duration_weeks": 5,
            "language": "中文",
            "constraints": "",
        },
    )
    assert response.status_code == 400
    assert "Tavily API Key" in response.json()["detail"]
    assert "大模型 API Key" in response.json()["detail"]


def test_invalid_plan_language_is_rejected_before_queueing(client: TestClient, registered_user: dict):
    response = client.post(
        "/api/plans",
        headers=auth_headers(registered_user["access_token"]),
        json={
            "topic": "Kubernetes",
            "goal": "能够部署一个带健康检查的 Web 服务",
            "level": "入门",
            "weekly_hours": 4,
            "duration_weeks": 5,
            "language": "火星文",
            "constraints": "",
        },
    )
    assert response.status_code == 422


def test_retry_clears_previous_generated_results(client: TestClient, registered_user: dict):
    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=registered_user["user"]["id"],
            topic="Rust 所有权",
            goal="能够写出不依赖克隆的 Rust 数据处理程序",
            level="入门",
            weekly_hours=5,
            duration_weeks=4,
            status="completed",
            stage="计划生成完成",
            progress=100,
            roadmap={"title": "旧路线"},
            resources=[{"id": "S1"}],
            evaluation={"total_score": 90},
            report_markdown="# 旧报告",
            model_name="openai/old-model",
            cost_usd=0.12,
            completed_at=datetime.now(UTC),
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/plans/{plan_id}/retry",
        headers=auth_headers(registered_user["access_token"]),
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["progress"] == 0
    for field in ("roadmap", "resources", "evaluation", "model_name", "cost_usd", "completed_at"):
        assert payload[field] is None
    assert (
        client.get(
            f"/api/plans/{plan_id}/report",
            headers=auth_headers(registered_user["access_token"]),
        ).status_code
        == 404
    )


def test_active_plan_cannot_be_retried(client: TestClient, registered_user: dict):
    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=registered_user["user"]["id"],
            topic="Rust 所有权",
            goal="能够写出不依赖克隆的 Rust 数据处理程序",
            level="入门",
            weekly_hours=5,
            duration_weeks=4,
            status="running",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/plans/{plan_id}/retry",
        headers=auth_headers(registered_user["access_token"]),
    )
    assert response.status_code == 409


def test_running_plan_can_be_stopped_and_retried(client: TestClient, registered_user: dict):
    headers = auth_headers(registered_user["access_token"])
    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=registered_user["user"]["id"],
            topic="可停止任务",
            goal="确认运行中的计划可以停止并在之后重新生成",
            level="入门",
            weekly_hours=5,
            duration_weeks=4,
            status="running",
            stage="CrewAI 正在编排路线",
            progress=38,
            started_at=datetime.now(UTC),
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    assert client.delete(f"/api/plans/{plan_id}", headers=headers).status_code == 409
    stopped = client.post(f"/api/plans/{plan_id}/stop", headers=headers)
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "cancelled"
    assert stopped.json()["completed_at"] is not None
    assert stopped.json()["stage"] == "已停止生成"

    retried = client.post(f"/api/plans/{plan_id}/retry", headers=headers)
    assert retried.status_code == 202
    assert retried.json()["status"] == "queued"
    assert retried.json()["started_at"] is None
    assert retried.json()["completed_at"] is None


def test_finished_plan_cannot_be_stopped(client: TestClient, registered_user: dict):
    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=registered_user["user"]["id"],
            topic="已完成任务",
            goal="确认已经完成的计划不会再次进入停止状态",
            level="入门",
            weekly_hours=5,
            duration_weeks=4,
            status="completed",
            progress=100,
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    response = client.post(
        f"/api/plans/{plan_id}/stop",
        headers=auth_headers(registered_user["access_token"]),
    )
    assert response.status_code == 409


def test_reports_and_deletion_are_user_scoped(client: TestClient, registered_user: dict):
    bob = client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "another-password", "display_name": "Bob"},
    ).json()
    alice_headers = auth_headers(registered_user["access_token"])
    bob_headers = auth_headers(bob["access_token"])

    with client.app.state.database.sessions() as session:
        plan = LearningPlan(
            user_id=registered_user["user"]["id"],
            topic="Rust 所有权",
            goal="能够写出不依赖克隆的 Rust 数据处理程序",
            level="入门",
            weekly_hours=5,
            duration_weeks=4,
            status="completed",
            stage="计划生成完成",
            progress=100,
            roadmap={"title": "Rust 路线"},
            resources=[],
            evaluation={"total_score": 90},
            report_markdown="# Rust 路线",
        )
        session.add(plan)
        session.commit()
        plan_id = plan.id

    assert client.get("/api/plans").status_code == 401
    assert client.get(f"/api/plans/{plan_id}/report", headers=bob_headers).status_code == 404
    assert client.delete(f"/api/plans/{plan_id}", headers=bob_headers).status_code == 404

    report = client.get(f"/api/plans/{plan_id}/report", headers=alice_headers)
    assert report.status_code == 200
    assert report.text == "# Rust 路线"
    assert "attachment" in report.headers["content-disposition"]

    assert client.delete(f"/api/plans/{plan_id}", headers=alice_headers).status_code == 204
    assert client.get(f"/api/plans/{plan_id}", headers=alice_headers).status_code == 404


def test_demo_report_has_route_resources_and_evaluation(client: TestClient):
    response = client.get("/api/demo")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["roadmap"]["stages"]) == 4
    assert {resource["id"] for resource in payload["resources"]} >= {"S1", "S8"}
    assert payload["evaluation"]["total_score"] >= 75
    assert "参考资料" in payload["report_markdown"]
    assert "#### 分步执行" in payload["report_markdown"]
    assert "#### 验收标准" in payload["report_markdown"]
    assert "本阶段依据" in payload["report_markdown"]
