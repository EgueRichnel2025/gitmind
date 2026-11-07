"""GitMind command-line interface."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gitmind import __version__
from gitmind.core.ai import (
    AIConfigurationError,
    AIContextError,
    AIProviderConfig,
    AIProviderError,
    CommitSuggestionService,
    OpenAICompatibleProvider,
)
from gitmind.core.analysis.content import (
    FileContentReadError,
    UnsafeFilePathError,
)
from gitmind.core.analysis.models import FileAnalysisSnapshot
from gitmind.core.analysis.service import FileAnalysisService
from gitmind.core.git.errors import GitRepositoryNotFoundError, GitRunnerError
from gitmind.core.git.repository import RepositoryDetector
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.status_service import GitStatusService
from gitmind.core.git.summary import GitStatusSummarizer
from gitmind.core.selection.service import FileSelectionService
from gitmind.ui.commit_suggestions import CommitSuggestionTerminalUI
from gitmind.ui.selection import SelectionTerminalUI

app = typer.Typer(
    name="gitmind",
    help="An AI-powered assistant for your Git workflow.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)


def display_analysis_summary(
    console: Console,
    snapshot: FileAnalysisSnapshot,
) -> None:
    """Display a summary of the selected files analysis."""
    table = Table.grid(padding=(0, 3))
    table.add_column(style="bold")
    table.add_column(justify="right")

    table.add_row("Files analyzed", str(snapshot.file_count))
    table.add_row("Files with staged changes", str(snapshot.staged_diff_count))
    table.add_row("Files with unstaged changes", str(snapshot.unstaged_diff_count))
    table.add_row("Binary files", str(snapshot.binary_count))
    table.add_row("Truncated contents", str(snapshot.content_truncated_count))
    table.add_row("Truncated diffs", str(snapshot.diff_truncated_count))

    console.print(
        Panel(
            table,
            title="GitMind | Analysis completed",
            border_style="green",
            expand=False,
        )
    )

    if snapshot.files:
        console.print("[bold]Analyzed files:[/bold]")

        for file_analysis in snapshot.files:
            console.print(f"  [dim]• {file_analysis.path}[/dim]")


def run_commit_suggestion_workflow(
    console: Console,
    analysis: FileAnalysisSnapshot,
) -> None:
    """Generate and interactively select AI commit message suggestions."""
    try:
        config = AIProviderConfig.from_env()

    except AIConfigurationError as error:
        console.print(
            Panel(
                (
                    "AI commit suggestions are not configured.\n\n"
                    f"{error}\n\n"
                    "Configure these environment variables in Git Bash:\n"
                    "  GITMIND_AI_API_KEY\n"
                    "  GITMIND_AI_MODEL\n\n"
                    "GITMIND_AI_BASE_URL is optional. "
                    "Its default value points to Groq."
                ),
                title="GitMind | AI Configuration",
                border_style="yellow",
                expand=False,
            )
        )
        console.print("[yellow]AI suggestions skipped. Repository unchanged.[/yellow]")
        return

    provider = OpenAICompatibleProvider(config)
    service = CommitSuggestionService(provider=provider)

    try:
        suggestions = service.generate(analysis)

    except (AIContextError, AIProviderError) as error:
        console.print(
            Panel(
                f"Unable to generate commit suggestions:\n{error}",
                title="GitMind | AI Error",
                border_style="red",
                expand=False,
            )
        )
        console.print("[yellow]No commit message was selected. Repository unchanged.[/yellow]")
        return

    console.print(
        Panel.fit(
            "Three commit message suggestions generated successfully.",
            title="GitMind | AI Generation",
            border_style="green",
        )
    )

    suggestion_ui = CommitSuggestionTerminalUI(
        suggestions=suggestions,
        console=console,
    )

    selected_message = suggestion_ui.run()

    if selected_message is None:
        console.print("[yellow]Suggestion selection cancelled. Repository unchanged.[/yellow]")
        return

    console.print(
        Panel(
            Text(selected_message, style="bold green"),
            title="GitMind | Selected Commit Message",
            border_style="green",
            expand=False,
        )
    )

    console.print(
        "[dim]Message selected only. No Git staging, commit or push operation was performed.[/dim]"
    )


def run_selection_workflow() -> None:
    """Detect repository changes, select files and analyze them."""
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
            "Starting read-only file analysis.\n"
            "Selected change context will be sent to your configured AI provider "
            "to generate commit suggestions.\n"
            "[dim]No Git staging or commit operation will be performed.[/dim]",
            title="GitMind",
            border_style="green",
        )
    )

    try:
        analysis = FileAnalysisService(
            repository_root=repository.root,
        ).analyze(selection)

    except (
        GitRunnerError,
        FileContentReadError,
        UnsafeFilePathError,
    ) as error:
        console.print(
            Text(
                f"Unable to analyze selected files: {error}",
                style="bold red",
            )
        )
        raise typer.Exit(code=1) from error

    display_analysis_summary(console, analysis)

    run_commit_suggestion_workflow(console, analysis)


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
