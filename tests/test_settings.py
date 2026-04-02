"""Tests for SimpliSettings base class."""

import pytest

from simpli_core.settings import SimpliSettings


class TestSimplicSettings:
    def test_defaults(self) -> None:
        settings = SimpliSettings()
        assert settings.app_env == "development"
        assert settings.app_host == "0.0.0.0"
        assert settings.app_port == 8000
        assert settings.app_log_level == "info"
        assert settings.app_debug is False

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_PORT", "9000")
        monkeypatch.setenv("APP_DEBUG", "true")
        settings = SimpliSettings()
        assert settings.app_env == "production"
        assert settings.app_port == 9000
        assert settings.app_debug is True

    def test_subclass_extension(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class ServiceSettings(SimpliSettings):
            litellm_model: str = "openai/gpt-4o"
            database_url: str = ""

        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("LITELLM_MODEL", "anthropic/claude-sonnet")
        settings = ServiceSettings()
        assert settings.app_env == "staging"
        assert settings.litellm_model == "anthropic/claude-sonnet"
        assert settings.database_url == ""
