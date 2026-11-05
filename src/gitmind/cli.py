"""GitMind command-line interface."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from gitmind import __version__
from gitmind.core.git.errors import GitRepositoryNotFoundError, GitRunnerError
from gitmind.core.git.repository import RepositoryDetector
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.status_service import GitStatusService
from gitmind.core.git.summary import GitStatusSummarizer
from gitmind.core.selection.service import FileSelectionService
from gitmind.ui.selection import SelectionTerminalUI

app = typer.Typer(
    name="gitmind",
    help="An AI-powered assistant for your Git workflow.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)


def run_selection_workflow() -> None:
    """Detect repository changes and launch interactive file selection."""
    console = Console()
    runner = GitRunner()

    try:
        repository = RepositoryDetector(runner).discover(Path.cwd())

        if repository is None:
            console.print("[bold red]Error: Not inside a Git repository.[/bold red]")
            raise typer.Exit(code=1)

        snapshot = GitStatusService(runner=runner).get_status(repository.root)

    except (GitRepositoryNotFoundError, GitRunnerError) as error:
        message = Text(
            f"Unable to inspect the Git repository: {error}",
            style="bold red",
        )
        console.print(message)
        raise typer.Exit(code=1) from error

    summary = GitStatusSummarizer().summarize(snapshot)

    repository_info = Text()
    repository_info.append("Repository: ", style="bold")
    repository_info.append(str(repository.root))
    repository_info.append("\nDetected changes: ", style="bold")
    repository_info.append(f"{summary.total_files} files")
    repository_info.append("\nStaged: ", style="bold")
    repository_info.append(str(summary.staged_files))
    repository_info.append(" | Unstaged: ", style="bold")
    repository_info.append(str(summary.unstaged_files))
    repository_info.append(" | Untracked: ", style="bold")
    repository_info.append(str(summary.untracked_files))

    console.print(
        Panel(
            repository_info,
            title="GitMind",
            border_style="cyan",
            expand=False,
        )
    )

    if not summary.has_changes:
        console.print("[green]No changes detected. Working tree is clean.[/green]")
        return

    selection_service = FileSelectionService(snapshot=snapshot)

    selection_ui = SelectionTerminalUI(
        service=selection_service,
        console=console,
    )

    selection = selection_ui.run()

    if selection is None:
        if getattr(selection_ui, "quit_confirmed", False) is True:
            console.print("[yellow]GitMind closed. Repository unchanged.[/yellow]")
        else:
            console.print("[yellow]Selection cancelled. Repository unchanged.[/yellow]")
        return

    if not selection.has_selection:
        console.print("[yellow]No files selected. Nothing to analyze.[/yellow]")
        return

    count = selection.selected_count
    label = "file" if count == 1 else "files"

    console.print(
        Panel.fit(
            f"[bold green]Selection confirmed: {count} {label}.[/bold green]\n"
            "The selected files are ready for analysis.\n"
            "[dim]No Git staging or commit operation was performed.[/dim]",
            title="GitMind",
            border_style="green",
        )
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

    run_selection_workflow()
