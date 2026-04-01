"""Tests for simpli-core configuration loader."""

from pathlib import Path

import pytest

from simpli_core.config import SimpliConfig, load_config


class TestLoadConfig:
    def test_load_from_yaml(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("simpli_env: production\nsimpli_debug: true\n")
        config = load_config(yaml_file=yaml_file)
        assert config.simpli_env == "production"
        assert config.simpli_debug is True

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text(":\n  - :\n    bad: [unterminated")
        with pytest.raises(ValueError, match="Failed to parse YAML"):
            load_config(yaml_file=yaml_file)

    def test_missing_yaml_ignored(self) -> None:
        config = load_config(yaml_file="/nonexistent/config.yaml")
        assert config.simpli_env == "development"

    def test_env_vars_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("simpli_env: staging\n")
        monkeypatch.setenv("SIMPLI_ENV", "production")
        config = load_config(yaml_file=yaml_file)
        assert config.simpli_env == "production"

    def test_env_file_loading(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("SIMPLI_LOG_LEVEL=DEBUG\n")
        config = load_config(env_file=env_file)
        assert config.simpli_log_level == "DEBUG"

    def test_defaults(self) -> None:
        config = SimpliConfig()
        assert config.simpli_env == "development"
        assert config.simpli_debug is False
        assert config.simpli_log_level == "INFO"

    def test_extra_keys_allowed(self) -> None:
        config = SimpliConfig.model_validate({"simpli_custom_key": "value"})
        assert config.model_extra is not None
        assert config.model_extra["simpli_custom_key"] == "value"

    def test_non_simpli_env_vars_excluded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OTHER_VAR", "should_not_appear")
        config = load_config()
        assert "other_var" not in (config.model_extra or {})

    def test_yaml_non_dict_ignored(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2\n")
        config = load_config(yaml_file=yaml_file)
        assert config.simpli_env == "development"

    def test_bool_coercion_from_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SIMPLI_DEBUG", "true")
        config = load_config()
        assert config.simpli_debug is True
