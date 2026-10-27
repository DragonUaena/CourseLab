from pathlib import Path

from app.config import Settings


def test_prefixed_environment_names_are_supported():
    settings = Settings.model_validate(
        {
            "COURSELAB_SECRET_KEY": "prefixed-secret",
            "COURSELAB_DATABASE_URL": "sqlite:///prefixed.db",
            "COURSELAB_LLM_MODEL": "openai/test-model",
            "TAVILY_API_KEY": "tvly-test",
        }
    )
    assert settings.secret_key == "prefixed-secret"
    assert settings.database_url == "sqlite:///prefixed.db"
    assert settings.llm_model == "openai/test-model"
    assert settings.tavily_api_key == "tvly-test"


def test_comma_separated_cors_origins_are_read_from_env_file(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "COURSELAB_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=env_file)
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
