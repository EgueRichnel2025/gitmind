"""Tests for the Questionary-based file selection interface."""

from io import StringIO
from unittest.mock import Mock

import pytest
from rich.console import Console

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot
from gitmind.core.selection.models import FileSelectionSnapshot
from gitmind.core.selection.service import FileSelectionService
from gitmind.ui.selection import SelectionTerminalUI


def make_service() -> FileSelectionService:
    """Create a selection service containing three files."""
    files = (
        GitFileStatus("src/auth.py", " ", "M"),
        GitFileStatus("src/main.py", " ", "M"),
        GitFileStatus("README.md", "?", "?"),
    )

    return FileSelectionService(GitStatusSnapshot(files=files))


def make_ui(
    service: FileSelectionService,
    answer: list[str] | None,
) -> tuple[SelectionTerminalUI, StringIO, Mock]:
    """Create a UI with a simulated Questionary response."""
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None)

    checkbox_prompt = Mock()
    checkbox_prompt.return_value.ask.return_value = answer

    ui = SelectionTerminalUI(
        service=service,
        console=console,
        checkbox_prompt=checkbox_prompt,
    )

    return ui, output, checkbox_prompt


def test_ui_builds_checkbox_choices_for_all_files() -> None:
    service = make_service()
    ui, output, prompt = make_ui(service, ["src/auth.py"])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_paths == ("src/auth.py",)

    choices = prompt.call_args.kwargs["choices"]

    assert [choice.value for choice in choices] == [
        "src/auth.py",
        "src/main.py",
        "README.md",
    ]
    assert "[MODIFIED · UNSTAGED]" in choices[0].title
    assert "[UNTRACKED]" in choices[2].title
    assert "GitMind" in output.getvalue()


def test_ui_configures_arrow_keys_space_and_selection_shortcuts() -> None:
    service = make_service()
    ui, _, prompt = make_ui(service, [])

    ui.run()

    options = prompt.call_args.kwargs

    assert options["use_arrow_keys"] is True
    assert options["use_jk_keys"] is False
    assert options["use_emacs_keys"] is False
    assert "Space Select" in options["instruction"]
    assert "A Select all" in options["instruction"]
    assert "I Invert" in options["instruction"]


def test_ui_replaces_previous_selection_with_confirmed_choices() -> None:
    service = make_service()
    service.select("src/auth.py")

    ui, _, _ = make_ui(service, ["src/main.py", "README.md"])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_paths == ("src/main.py", "README.md")


def test_ui_preserves_original_file_order() -> None:
    service = make_service()

    ui, _, _ = make_ui(service, ["README.md", "src/auth.py"])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_paths == ("src/auth.py", "README.md")


def test_ui_accepts_empty_selection() -> None:
    service = make_service()

    ui, _, _ = make_ui(service, [])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_count == 0


def test_ui_cancellation_returns_none_and_preserves_selection() -> None:
    service = make_service()
    service.select("src/auth.py")

    ui, _, _ = make_ui(service, None)

    result = ui.run()

    assert result is None
    assert service.get_selection().selected_paths == ("src/auth.py",)


def test_ui_handles_keyboard_interrupt() -> None:
    service = make_service()
    ui, _, prompt = make_ui(service, [])

    prompt.return_value.ask.side_effect = KeyboardInterrupt

    assert ui.run() is None


def test_ui_handles_end_of_input() -> None:
    service = make_service()
    ui, _, prompt = make_ui(service, [])

    prompt.return_value.ask.side_effect = EOFError

    assert ui.run() is None


def test_ui_rejects_unknown_paths_from_prompt() -> None:
    service = make_service()
    ui, _, _ = make_ui(service, ["missing.py"])

    with pytest.raises(ValueError, match="Unknown selected file paths"):
        ui.run()


def test_ui_rejects_invalid_prompt_result() -> None:
    service = make_service()
    ui, _, prompt = make_ui(service, [])

    prompt.return_value.ask.return_value = "src/auth.py"

    with pytest.raises(TypeError, match="list of file paths"):
        ui.run()


def test_ui_returns_empty_snapshot_without_opening_prompt() -> None:
    service = FileSelectionService(GitStatusSnapshot(files=()))
    ui, _, prompt = make_ui(service, [])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.total_count == 0
    prompt.assert_not_called()


def test_ui_rejects_invalid_service() -> None:
    with pytest.raises(TypeError, match="FileSelectionService"):
        SelectionTerminalUI(None)  # type: ignore[arg-type]
