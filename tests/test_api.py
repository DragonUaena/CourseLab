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


def test_demo_report_has_route_resources_and_evaluation(client: TestClient):
    response = client.get("/api/demo")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["roadmap"]["stages"]) == 4
    assert {resource["id"] for resource in payload["resources"]} >= {"S1", "S8"}
    assert payload["evaluation"]["total_score"] >= 75
    assert "参考资料" in payload["report_markdown"]
