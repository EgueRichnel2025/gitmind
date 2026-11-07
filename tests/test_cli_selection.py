"""Integration tests for the GitMind file selection CLI."""

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import gitmind.cli as cli_module
from gitmind.cli import app
from gitmind.ui.selection import SelectionTerminalUI

runner = CliRunner()


@pytest.fixture(autouse=True)
def disable_live_ai_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent CLI tests from making real AI provider requests."""
    monkeypatch.delenv("GITMIND_AI_API_KEY", raising=False)
    monkeypatch.delenv("GITMIND_AI_MODEL", raising=False)
    monkeypatch.delenv("GITMIND_AI_BASE_URL", raising=False)
    monkeypatch.setattr(
        cli_module.StagingConfirmationTerminalUI,
        "run",
        lambda self: True,
    )


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


def confirm_first_file(ui: SelectionTerminalUI):
    """Simulate confirmation after selecting the first file."""
    snapshot = ui._service.get_selection()

    if snapshot.files:
        ui._service.select(snapshot.files[0].path)

    return ui._service.get_selection()


def test_cli_reports_error_outside_git_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app)

    assert result.exit_code == 1
    assert "Not inside a Git repository" in result.output


def test_cli_reports_clean_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "No changes detected" in result.output


def test_cli_runs_selection_and_stages_only_selected_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_text("# GitMind\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(SelectionTerminalUI, "run", confirm_first_file)

    result = runner.invoke(app)

    assert result.exit_code == 0, result.output
    assert "Detected changes: 2 files" in result.output
    assert "Selection confirmed: 1 file" in result.output

    status = get_git_status(tmp_path)

    assert "A  README.md" in status
    assert "?? app.py" in status


def test_cli_cancellation_does_not_stage_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_text("# GitMind\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(SelectionTerminalUI, "run", lambda self: None)

    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "Selection cancelled" in result.output
    assert "?? README.md" in get_git_status(tmp_path)


def test_cli_handles_empty_selection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_text("# GitMind\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        lambda self: self._service.get_selection(),
    )

    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "No files selected" in result.output
    assert "?? README.md" in get_git_status(tmp_path)
