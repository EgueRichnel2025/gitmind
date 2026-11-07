"""Tests for the commit confirmation terminal interface."""

from io import StringIO
from typing import Any

import pytest
from rich.console import Console

from gitmind.core.git.status_models import GitFileStatus
from gitmind.core.selection.models import (
    FileSelectionSnapshot,
    SelectableFile,
)
from gitmind.ui.commit_confirmation import CommitConfirmationTerminalUI

COMMIT_MESSAGE = "feat: add selected-file commit workflow"


class FakePrompt:
    """Represent a questionary prompt in tests."""

    def __init__(self, result: Any = True) -> None:
        self.result = result

    def ask(self) -> Any:
        """Return the configured prompt result."""
        if isinstance(self.result, BaseException):
            raise self.result

        return self.result


def build_selection() -> FileSelectionSnapshot:
    """Build a selection containing one selected and one unselected file."""
    return FileSelectionSnapshot(
        files=(
            SelectableFile(
                git_file=GitFileStatus(
                    path="src/app.py",
                    index_status="M",
                    worktree_status=" ",
                ),
                selected=True,
            ),
            SelectableFile(
                git_file=GitFileStatus(
                    path="README.md",
                    index_status="M",
                    worktree_status=" ",
                ),
                selected=False,
            ),
        )
    )


def build_ui(
    result: Any = True,
    console: Console | None = None,
    prompt_calls: list[tuple[str, dict[str, Any]]] | None = None,
) -> CommitConfirmationTerminalUI:
    """Build the interface with a fake confirmation prompt."""

    def confirm_prompt(question: str, **kwargs: Any) -> FakePrompt:
        if prompt_calls is not None:
            prompt_calls.append((question, kwargs))

        return FakePrompt(result)

    return CommitConfirmationTerminalUI(
        selection=build_selection(),
        message=COMMIT_MESSAGE,
        console=console,
        confirm_prompt=confirm_prompt,
    )


def test_commit_confirmation_accepts_explicit_yes() -> None:
    ui = build_ui(result=True)

    assert ui.run() is True


def test_commit_confirmation_returns_false_when_declined() -> None:
    ui = build_ui(result=False)

    assert ui.run() is False


def test_commit_confirmation_returns_false_when_cancelled() -> None:
    ui = build_ui(result=None)

    assert ui.run() is False


@pytest.mark.parametrize(
    "exception",
    [
        KeyboardInterrupt(),
        EOFError(),
    ],
)
def test_commit_confirmation_returns_false_on_prompt_interruption(
    exception: BaseException,
) -> None:
    ui = build_ui(result=exception)

    assert ui.run() is False


def test_commit_confirmation_uses_negative_default() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    ui = build_ui(
        result=True,
        prompt_calls=calls,
    )

    assert ui.run() is True
    assert calls == [
        (
            "Create this commit?",
            {"default": False},
        )
    ]


def test_commit_confirmation_displays_selected_files_and_message() -> None:
    console = Console(
        file=StringIO(),
        record=True,
        width=100,
    )

    ui = build_ui(
        result=True,
        console=console,
    )

    ui.run()

    output = console.export_text()

    assert "GitMind | Commit Confirmation" in output
    assert "src/app.py" in output
    assert COMMIT_MESSAGE in output
    assert "README.md" not in output
    assert "Create this commit?" in output


def test_commit_confirmation_rejects_invalid_selection() -> None:
    with pytest.raises(TypeError, match="FileSelectionSnapshot"):
        CommitConfirmationTerminalUI(
            selection="invalid",  # type: ignore[arg-type]
            message=COMMIT_MESSAGE,
        )


def test_commit_confirmation_rejects_empty_selection() -> None:
    with pytest.raises(ValueError, match="without selected files"):
        CommitConfirmationTerminalUI(
            selection=FileSelectionSnapshot(files=()),
            message=COMMIT_MESSAGE,
        )


def test_commit_confirmation_rejects_invalid_message_type() -> None:
    with pytest.raises(TypeError, match="message must be a string"):
        CommitConfirmationTerminalUI(
            selection=build_selection(),
            message=None,  # type: ignore[arg-type]
        )


def test_commit_confirmation_rejects_empty_message() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        CommitConfirmationTerminalUI(
            selection=build_selection(),
            message="   ",
        )


@pytest.mark.parametrize(
    "invalid_result",
    [
        "yes",
        1,
        0,
    ],
)
def test_commit_confirmation_rejects_non_boolean_prompt_result(
    invalid_result: Any,
) -> None:
    ui = build_ui(result=invalid_result)

    with pytest.raises(TypeError, match="boolean or None"):
        ui.run()
