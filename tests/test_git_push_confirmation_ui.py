"""Tests for the push confirmation terminal interface."""

from io import StringIO
from typing import Any

import pytest
from rich.console import Console

from gitmind.core.git.commit_models import GitCommitResult
from gitmind.ui.push_confirmation import PushConfirmationTerminalUI

COMMIT = GitCommitResult(
    commit_hash="a" * 40,
    message="feat: add selected-file commit workflow",
    committed_paths=("src/app.py",),
)


class FakePrompt:
    """Represent a questionary prompt in tests."""

    def __init__(self, result: Any = True) -> None:
        self.result = result

    def ask(self) -> Any:
        """Return the configured prompt result."""
        if isinstance(self.result, BaseException):
            raise self.result

        return self.result


def build_ui(
    result: Any = True,
    console: Console | None = None,
    prompt_calls: list[tuple[str, dict[str, Any]]] | None = None,
) -> PushConfirmationTerminalUI:
    """Build the interface with a fake confirmation prompt."""

    def confirm_prompt(question: str, **kwargs: Any) -> FakePrompt:
        if prompt_calls is not None:
            prompt_calls.append((question, kwargs))

        return FakePrompt(result)

    return PushConfirmationTerminalUI(
        commit=COMMIT,
        branch="phase/ai-commit-suggestions",
        console=console,
        confirm_prompt=confirm_prompt,
    )


def test_push_confirmation_accepts_explicit_yes() -> None:
    assert build_ui(result=True).run() is True


def test_push_confirmation_returns_false_when_declined() -> None:
    assert build_ui(result=False).run() is False


def test_push_confirmation_returns_false_when_cancelled() -> None:
    assert build_ui(result=None).run() is False


@pytest.mark.parametrize(
    "exception",
    [
        KeyboardInterrupt(),
        EOFError(),
    ],
)
def test_push_confirmation_returns_false_on_prompt_interruption(
    exception: BaseException,
) -> None:
    assert build_ui(result=exception).run() is False


def test_push_confirmation_uses_negative_default() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    assert (
        build_ui(
            result=True,
            prompt_calls=calls,
        ).run()
        is True
    )

    assert calls == [
        (
            "Push this commit to the remote repository?",
            {"default": False},
        )
    ]


def test_push_confirmation_displays_commit_and_branch() -> None:
    console = Console(
        file=StringIO(),
        record=True,
        width=110,
    )

    build_ui(
        result=True,
        console=console,
    ).run()

    output = console.export_text()

    assert "GitMind | Push Confirmation" in output
    assert "aaaaaaaaaaaa" in output
    assert "phase/ai-commit-suggestions" in output
    assert COMMIT.message in output
    assert "Push this commit to the remote repository?" in output


def test_push_confirmation_rejects_invalid_commit() -> None:
    with pytest.raises(TypeError, match="GitCommitResult"):
        PushConfirmationTerminalUI(
            commit="invalid",  # type: ignore[arg-type]
            branch="main",
        )


def test_push_confirmation_rejects_invalid_branch_type() -> None:
    with pytest.raises(TypeError, match="branch must be a string"):
        PushConfirmationTerminalUI(
            commit=COMMIT,
            branch=None,  # type: ignore[arg-type]
        )


def test_push_confirmation_rejects_empty_branch() -> None:
    with pytest.raises(ValueError, match="branch cannot be empty"):
        PushConfirmationTerminalUI(
            commit=COMMIT,
            branch="   ",
        )


@pytest.mark.parametrize(
    "invalid_result",
    [
        "yes",
        1,
        0,
    ],
)
def test_push_confirmation_rejects_non_boolean_prompt_result(
    invalid_result: Any,
) -> None:
    with pytest.raises(TypeError, match="boolean or None"):
        build_ui(result=invalid_result).run()
