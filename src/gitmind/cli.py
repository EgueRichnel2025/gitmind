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
from gitmind.core.analysis.models import (
    FileAnalysisSnapshot,
)
from gitmind.core.analysis.service import FileAnalysisService
from gitmind.core.git.commit import GitCommitService
from gitmind.core.git.commit_errors import GitCommitError
from gitmind.core.git.errors import GitRepositoryNotFoundError, GitRunnerError
from gitmind.core.git.repository import RepositoryDetector
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.staging import GitStagingService
from gitmind.core.git.staging_errors import GitStagingError
from gitmind.core.git.staging_models import GitStagingResult
from gitmind.core.git.status_models import GitStatusSnapshot
from gitmind.core.git.status_service import GitStatusService
from gitmind.core.git.summary import GitStatusSummarizer
from gitmind.core.selection.models import (
    FileSelectionSnapshot,
    SelectableFile,
)
from gitmind.core.selection.service import FileSelectionService
from gitmind.ui.commit_confirmation import CommitConfirmationTerminalUI
from gitmind.ui.commit_suggestions import CommitSuggestionTerminalUI
from gitmind.ui.selection import SelectionTerminalUI
from gitmind.ui.staging_confirmation import StagingConfirmationTerminalUI

app = typer.Typer(
    name="git-mind",
    help="An AI-powered assistant for your Git workflow.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
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


def build_staged_selection(
    status_snapshot: GitStatusSnapshot,
    staging_result: GitStagingResult,
) -> FileSelectionSnapshot:
    """Build a fresh selection containing only the files staged by GitMind."""
    selected_paths = set(staging_result.selected_paths)
    covered_paths: set[str] = set()
    selected_files: list[SelectableFile] = []

    for git_file in status_snapshot.files:
        file_paths = {git_file.path}

        if git_file.original_path is not None:
            file_paths.add(git_file.original_path)

        matching_paths = file_paths.intersection(selected_paths)

        if not matching_paths:
            continue

        if not git_file.is_staged:
            raise GitStagingError(f"Selected file '{git_file.path}' was not staged successfully.")

        if git_file.is_unstaged:
            raise GitStagingError(
                f"File '{git_file.path}' still has unstaged changes after staging. "
                "Review the working tree and run GitMind again."
            )

        selected_files.append(
            SelectableFile(
                git_file=git_file,
                selected=True,
            )
        )

        covered_paths.update(matching_paths)

    missing_paths = selected_paths - covered_paths

    if missing_paths:
        paths = ", ".join(sorted(missing_paths))
        raise GitStagingError(f"Some selected files could not be found after staging: {paths}")

    return FileSelectionSnapshot(files=tuple(selected_files))


def run_commit_suggestion_workflow(
    console: Console,
    analysis: FileAnalysisSnapshot,
    repository_root: Path,
    selection: FileSelectionSnapshot,
    runner: GitRunner,
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
        console.print("[yellow]Selected files remain staged. No commit was created.[/yellow]")
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
        console.print("[yellow]Selected files remain staged. No commit was created.[/yellow]")
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
        console.print(
            "[yellow]Suggestion selection cancelled. "
            "Selected files remain staged. No commit was created.[/yellow]"
        )
        return

    console.print(
        Panel(
            Text(selected_message, style="bold green"),
            title="GitMind | Selected Commit Message",
            border_style="green",
            expand=False,
        )
    )

    confirmation_ui = CommitConfirmationTerminalUI(
        selection=selection,
        message=selected_message,
        console=console,
    )

    if not confirmation_ui.run():
        console.print(
            "[yellow]Commit declined. Selected files remain staged. No commit was created.[/yellow]"
        )
        return

    try:
        commit_result = GitCommitService(
            repository_root=repository_root,
            runner=runner,
        ).commit(
            selection=selection,
            message=selected_message,
        )

    except (GitCommitError, GitRunnerError) as error:
        console.print(
            Panel(
                f"Unable to create the commit:\\n{error}\\n\\n"
                "Inspect the repository status before continuing.",
                title="GitMind | Commit Error",
                border_style="red",
                expand=False,
            )
        )
        console.print(
            "[yellow]The commit was not completed. "
            "Review the staged changes before retrying.[/yellow]"
        )
        return

    commit_summary = Text()
    commit_summary.append("Commit created successfully.\\n\\n", style="bold green")
    commit_summary.append("Commit: ", style="bold")
    commit_summary.append(f"{commit_result.commit_hash[:12]}\\n", style="cyan")
    commit_summary.append("Message: ", style="bold")
    commit_summary.append(f"{commit_result.message}\\n\\n")
    commit_summary.append("Committed files:\\n", style="bold")

    for committed_path in commit_result.committed_paths:
        commit_summary.append("  ✓ ", style="green")
        commit_summary.append(f"{committed_path}\\n")

    console.print(
        Panel(
            commit_summary,
            title="GitMind | Commit Completed",
            border_style="green",
            expand=False,
        )
    )


def run_selection_workflow() -> None:
    """Select files, confirm staging, analyze staged changes and suggest a commit."""
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
            console.print("[yellow]GitMind closed. No staging was performed.[/yellow]")
        else:
            console.print("[yellow]Selection cancelled. No staging was performed.[/yellow]")
        return

    if not selection.has_selection:
        console.print("[yellow]No files selected. Nothing to stage.[/yellow]")
        return

    count = selection.selected_count
    label = "file" if count == 1 else "files"

    console.print(
        Panel.fit(
            f"[bold green]Selection confirmed: {count} {label}.[/bold green]\n"
            "GitMind will stage only the selected files after your confirmation.\n"
            "Their staged changes will then be analyzed for commit suggestions.\n"
            "[dim]No commit or push will be performed at this stage.[/dim]",
            title="GitMind",
            border_style="green",
        )
    )

    staging_ui = StagingConfirmationTerminalUI(
        selection=selection,
        console=console,
    )

    if not staging_ui.run():
        console.print("[yellow]Staging declined. No files were added to the index.[/yellow]")
        return

    try:
        staging_result = GitStagingService(
            repository_root=repository.root,
            runner=runner,
        ).stage(selection)

        refreshed_status = GitStatusService(
            runner=runner,
        ).get_status(repository.root)

        staged_selection = build_staged_selection(
            refreshed_status,
            staging_result,
        )

    except (GitRunnerError, GitStagingError) as error:
        console.print(
            Panel(
                f"Unable to stage the selected files:\n{error}\n\n"
                "Inspect the repository status before continuing.",
                title="GitMind | Staging Error",
                border_style="red",
                expand=False,
            )
        )
        raise typer.Exit(code=1) from error

    console.print(
        Panel.fit(
            f"[bold green]Staging completed: {staging_result.selected_count} "
            f"selected files.[/bold green]\n"
            "Only the selected paths were passed to Git.",
            title="GitMind | Staging Completed",
            border_style="green",
        )
    )

    try:
        analysis = FileAnalysisService(
            repository_root=repository.root,
        ).analyze(staged_selection)

    except (
        GitRunnerError,
        FileContentReadError,
        UnsafeFilePathError,
    ) as error:
        console.print(
            Panel(
                f"Unable to analyze staged changes:\n{error}\n\n"
                "The selected files remain staged. No commit was created.",
                title="GitMind | Analysis Error",
                border_style="red",
                expand=False,
            )
        )
        raise typer.Exit(code=1) from error

    display_analysis_summary(console, analysis)

    run_commit_suggestion_workflow(
        console=console,
        analysis=analysis,
        repository_root=repository.root,
        selection=staged_selection,
        runner=runner,
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
