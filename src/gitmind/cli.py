"""GitMind command-line interface."""

import typer

from gitmind import __version__

app = typer.Typer(
    name="gitmind",
    help="An AI-powered assistant for your Git workflow.",
    no_args_is_help=True,
    invoke_without_command=True,
    add_completion=False,
)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        is_eager=True,
        help="Display GitMind version and exit.",
    ),
) -> None:
    """GitMind - Your intelligent Git workflow assistant."""
    if version:
        typer.echo(f"GitMind {__version__}")
        raise typer.Exit()
