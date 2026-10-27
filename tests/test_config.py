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
