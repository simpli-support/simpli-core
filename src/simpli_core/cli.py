"""CLI interface for simpli-core."""

import typer

app = typer.Typer(help="Simpli Core CLI — shared utilities")


@app.command()
def version() -> None:
    """Show version."""
    from simpli_core import __version__

    typer.echo(f"simpli-core {__version__}")
