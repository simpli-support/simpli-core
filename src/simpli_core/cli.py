"""CLI interface for simpli-core."""

from pathlib import Path

import typer

app = typer.Typer(help="Simpli Core CLI — shared utilities")


@app.command()
def version() -> None:
    """Show the SDK version."""
    from simpli_core import __version__

    typer.echo(f"simpli-core {__version__}")


@app.command()
def config(
    env_file: str | None = typer.Option(None, help="Path to .env file"),
    yaml_file: str | None = typer.Option(None, help="Path to YAML config file"),
) -> None:
    """Show the resolved configuration."""
    from simpli_core.config import load_config

    env_path = Path(env_file) if env_file else None
    yaml_path = Path(yaml_file) if yaml_file else None
    try:
        cfg = load_config(env_file=env_path, yaml_file=yaml_path)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for key, value in sorted(cfg.model_dump().items()):
        typer.echo(f"{key}={value}")
    for key, value in sorted((cfg.model_extra or {}).items()):
        typer.echo(f"{key}={value}")
