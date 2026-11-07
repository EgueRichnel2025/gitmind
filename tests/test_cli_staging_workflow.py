"""Integration tests for the CLI staging confirmation workflow."""

import subprocess
from pathlib import Path

from typer.testing import CliRunner

import gitmind.cli as cli_module
from gitmind.ui.selection import SelectionTerminalUI

runner = CliRunner()


def initialize_repository(path: Path) -> None:
    """Initialize a temporary Git repository."""
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def get_git_status(path: Path) -> str:
    """Return the repository's porcelain Git status."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def get_staged_paths(path: Path) -> set[str]:
    """Return paths currently staged in the Git index."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def select_first_file(ui: SelectionTerminalUI):
    """Simulate selecting the first available file."""
    snapshot = ui._service.get_selection()

    if snapshot.files:
        ui._service.select(snapshot.files[0].path)

    return ui._service.get_selection()


def test_declining_staging_preserves_the_index_and_skips_analysis(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_text(
        "# GitMind\\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text(
        "print('hello')\\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        select_first_file,
    )

    monkeypatch.setattr(
        cli_module.StagingConfirmationTerminalUI,
        "run",
        lambda self: False,
    )

    class UnexpectedAnalysis:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("Analysis must not run after staging is declined.")

    class UnexpectedStaging:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("Staging must not run after staging is declined.")

    monkeypatch.setattr(
        cli_module,
        "FileAnalysisService",
        UnexpectedAnalysis,
    )

    monkeypatch.setattr(
        cli_module,
        "GitStagingService",
        UnexpectedStaging,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "Staging declined" in result.output
    assert "Analysis completed" not in result.output
    assert "AI Generation" not in result.output

    assert get_staged_paths(tmp_path) == set()

    status = get_git_status(tmp_path)
    assert "?? README.md" in status
    assert "?? app.py" in status
