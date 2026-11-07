"""Tests for the staging confirmation terminal interface."""

import pytest
from rich.console import Console

from gitmind.core.git.status_models import GitFileStatus
from gitmind.core.selection.models import (
    FileSelectionSnapshot,
    SelectableFile,
)
from gitmind.ui.staging_confirmation import StagingConfirmationTerminalUI


class FakePrompt:
    """Simulate a Questionary confirmation prompt."""

    def __init__(self, result=None, error=None) -> None:
        self._result = result
        self._error = error

    def ask(self):
        if self._error is not None:
            raise self._error

        return self._result


@pytest.fixture
def selection() -> FileSelectionSnapshot:
    """Create a selection with two selected files and one unselected file."""
    return FileSelectionSnapshot(
        files=(
            SelectableFile(
                git_file=GitFileStatus(
                    path="src/gitmind/cli.py",
                    index_status=" ",
                    worktree_status="M",
                ),
                selected=True,
            ),
            SelectableFile(
                git_file=GitFileStatus(
                    path="README.md",
                    index_status=" ",
                    worktree_status="M",
                ),
                selected=False,
            ),
            SelectableFile(
                git_file=GitFileStatus(
                    path="tests/test_cli.py",
                    index_status="?",
                    worktree_status="?",
                ),
                selected=True,
            ),
        )
    )


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (True, True),
        (False, False),
        (None, False),
    ],
)
def test_confirmation_returns_user_decision(
    selection: FileSelectionSnapshot,
    answer: bool | None,
    expected: bool,
) -> None:
    console = Console(record=True)

    ui = StagingConfirmationTerminalUI(
        selection=selection,
        console=console,
        confirm_prompt=lambda *args, **kwargs: FakePrompt(result=answer),
    )

    assert ui.run() is expected


def test_confirmation_defaults_to_no(
    selection: FileSelectionSnapshot,
) -> None:
    captured = {}

    def fake_confirm(message, **kwargs):
        captured["message"] = message
        captured.update(kwargs)
        return FakePrompt(result=False)

    ui = StagingConfirmationTerminalUI(
        selection=selection,
        console=Console(record=True),
        confirm_prompt=fake_confirm,
    )

    assert ui.run() is False
    assert captured["message"] == "Stage selected files?"
    assert captured["default"] is False


def test_confirmation_displays_only_selected_files(
    selection: FileSelectionSnapshot,
) -> None:
    console = Console(record=True)

    ui = StagingConfirmationTerminalUI(
        selection=selection,
        console=console,
        confirm_prompt=lambda *args, **kwargs: FakePrompt(result=False),
    )

    ui.run()

    output = console.export_text()

    assert "GitMind | Staging Confirmation" in output
    assert "The following files will be staged" in output
    assert "src/gitmind/cli.py" in output
    assert "tests/test_cli.py" in output
    assert "README.md" not in output
    assert "Do you want to stage these files?" in output


@pytest.mark.parametrize(
    "error",
    [
        KeyboardInterrupt(),
        EOFError(),
    ],
)
def test_confirmation_handles_interruption(
    selection: FileSelectionSnapshot,
    error: Exception,
) -> None:
    ui = StagingConfirmationTerminalUI(
        selection=selection,
        console=Console(record=True),
        confirm_prompt=lambda *args, **kwargs: FakePrompt(error=error),
    )

    assert ui.run() is False


def test_confirmation_rejects_unexpected_prompt_result(
    selection: FileSelectionSnapshot,
) -> None:
    ui = StagingConfirmationTerminalUI(
        selection=selection,
        console=Console(record=True),
        confirm_prompt=lambda *args, **kwargs: FakePrompt(result="yes"),
    )

    with pytest.raises(TypeError, match="boolean or None"):
        ui.run()


def test_confirmation_rejects_invalid_selection_type() -> None:
    with pytest.raises(TypeError, match="FileSelectionSnapshot"):
        StagingConfirmationTerminalUI(
            selection=None,  # type: ignore[arg-type]
        )


def test_confirmation_rejects_empty_selection() -> None:
    selection = FileSelectionSnapshot(files=())

    with pytest.raises(ValueError, match="without selected files"):
        StagingConfirmationTerminalUI(selection=selection)
