"""Integration tests for the GitMind CLI analysis workflow."""

import subprocess
from pathlib import Path

from typer.testing import CliRunner

import gitmind.cli as cli_module
from gitmind.core.analysis.content import FileContentReadError
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


def select_first_file(ui: SelectionTerminalUI):
    """Simulate confirmation with the first file selected."""
    snapshot = ui._service.get_selection()

    if snapshot.files:
        ui._service.select(snapshot.files[0].path)

    return ui._service.get_selection()


def test_cli_analyzes_confirmed_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_bytes(b"# GitMind\n")
    (tmp_path / "app.py").write_bytes(b"print('GitMind')\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(SelectionTerminalUI, "run", select_first_file)

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "Selection confirmed: 1 file" in result.output
    assert "Analysis completed" in result.output
    assert "Files analyzed" in result.output
    assert "1" in result.output
    assert "No Git staging or commit operation" in result.output

    # Analysis must not stage or commit any file.
    status = get_git_status(tmp_path)

    assert "?? README.md" in status
    assert "?? app.py" in status


def test_cli_does_not_analyze_after_cancellation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "app.py").write_bytes(b"value = 1\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        lambda self: None,
    )

    class UnexpectedAnalysis:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("Analysis must not start after cancellation.")

    monkeypatch.setattr(
        cli_module,
        "FileAnalysisService",
        UnexpectedAnalysis,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0
    assert "Selection cancelled" in result.output
    assert "Analysis completed" not in result.output


def test_cli_does_not_analyze_empty_selection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "app.py").write_bytes(b"value = 1\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        lambda self: self._service.get_selection(),
    )

    class UnexpectedAnalysis:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("Analysis must not start with an empty selection.")

    monkeypatch.setattr(
        cli_module,
        "FileAnalysisService",
        UnexpectedAnalysis,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0
    assert "No files selected" in result.output
    assert "Analysis completed" not in result.output


def test_cli_reports_analysis_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "app.py").write_bytes(b"value = 1\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(SelectionTerminalUI, "run", select_first_file)

    class FailedAnalysis:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def analyze(self, selection):
            raise FileContentReadError("simulated read failure")

    monkeypatch.setattr(
        cli_module,
        "FileAnalysisService",
        FailedAnalysis,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 1
    assert "Unable to analyze selected files" in result.output
    assert "simulated read failure" in result.output

    # An analysis error must not stage or commit anything.
    assert "?? app.py" in get_git_status(tmp_path)
