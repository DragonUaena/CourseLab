from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        secret_key="test-secret-key-with-enough-entropy",
        credential_key="test-credential-key",
        cors_origins=["http://localhost:5173"],
        tavily_api_key="",
        openai_api_key="",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def registered_user(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "correct-password", "display_name": "Alice"},
    )
    assert response.status_code == 201
    return response.json()
