"""Tests for simpli-core CLI."""

from typer.testing import CliRunner

from simpli_core import __version__
from simpli_core.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert __version__ in result.stdout
