"""Tests for simpli-core CLI."""

from typer.testing import CliRunner

from simpli_core import __version__
from simpli_core.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_config_command() -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "simpli_env=" in result.stdout
    assert "simpli_debug=" in result.stdout


def test_config_with_invalid_yaml(tmp_path) -> None:  # type: ignore[no-untyped-def]
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(":\n  bad: [unterminated")
    result = runner.invoke(app, ["config", "--yaml-file", str(bad_yaml)])
    assert result.exit_code == 1
