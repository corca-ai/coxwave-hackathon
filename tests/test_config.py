def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from shared.config import Settings

    settings = Settings()
    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "gpt-5-mini"
    assert settings.artifacts_dir == "artifacts"
