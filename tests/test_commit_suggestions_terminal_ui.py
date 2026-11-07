"""Tests for the interactive commit suggestion interface."""

from io import StringIO
from unittest.mock import Mock

import pytest
from rich.console import Console

from gitmind.core.ai.models import (
    CommitSuggestion,
    CommitSuggestionSet,
)
from gitmind.ui.commit_suggestions import CommitSuggestionTerminalUI

MESSAGES = (
    "feat(auth): implement authentication",
    "refactor(auth): simplify authentication flow",
    "test(auth): add authentication tests",
)


def make_suggestions() -> CommitSuggestionSet:
    """Create three valid commit suggestions."""
    return CommitSuggestionSet(
        suggestions=tuple(CommitSuggestion(message=message) for message in MESSAGES)
    )


def make_ui(
    answer: int | None,
) -> tuple[CommitSuggestionTerminalUI, StringIO, Mock]:
    """Create an interface with a simulated Questionary response."""
    output = StringIO()
    console = Console(
        file=output,
        force_terminal=False,
        color_system=None,
    )

    select_prompt = Mock()
    select_prompt.return_value.ask.return_value = answer

    ui = CommitSuggestionTerminalUI(
        suggestions=make_suggestions(),
        console=console,
        select_prompt=select_prompt,
    )

    return ui, output, select_prompt


def test_ui_displays_correct_title() -> None:
    ui, output, _ = make_ui(0)

    ui.run()

    assert "GitMind | Commit Suggestions" in output.getvalue()


def test_ui_builds_exactly_three_choices() -> None:
    ui, _, prompt = make_ui(0)

    ui.run()

    choices = prompt.call_args.kwargs["choices"]

    assert len(choices) == 3
    assert [choice.value for choice in choices] == [0, 1, 2]


def test_ui_preserves_suggestion_order() -> None:
    ui, _, prompt = make_ui(0)

    ui.run()

    choices = prompt.call_args.kwargs["choices"]

    assert choices[0].title.endswith(MESSAGES[0])
    assert choices[1].title.endswith(MESSAGES[1])
    assert choices[2].title.endswith(MESSAGES[2])


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (0, MESSAGES[0]),
        (1, MESSAGES[1]),
        (2, MESSAGES[2]),
    ],
)
def test_ui_returns_selected_message(
    answer: int,
    expected: str,
) -> None:
    ui, _, _ = make_ui(answer)

    assert ui.run() == expected


def test_ui_configures_keyboard_navigation() -> None:
    ui, _, prompt = make_ui(0)

    ui.run()

    options = prompt.call_args.kwargs

    assert options["use_shortcuts"] is False
    assert options["use_arrow_keys"] is True
    assert options["use_jk_keys"] is False
    assert options["use_emacs_keys"] is False
    assert "Enter Confirm" in options["instruction"]
    assert "Q Cancel" in options["instruction"]


def test_ui_returns_none_when_selection_is_cancelled() -> None:
    ui, _, _ = make_ui(None)

    assert ui.run() is None


def test_ui_handles_keyboard_interrupt() -> None:
    ui, _, prompt = make_ui(0)

    prompt.return_value.ask.side_effect = KeyboardInterrupt

    assert ui.run() is None


def test_ui_handles_end_of_input() -> None:
    ui, _, prompt = make_ui(0)

    prompt.return_value.ask.side_effect = EOFError

    assert ui.run() is None


@pytest.mark.parametrize(
    "invalid_answer",
    [
        "feat(auth): implement authentication",
        -1,
        3,
        True,
        1.5,
    ],
)
def test_ui_rejects_invalid_selection_result(
    invalid_answer: object,
) -> None:
    ui, _, prompt = make_ui(0)
    prompt.return_value.ask.return_value = invalid_answer

    with pytest.raises(TypeError, match="valid suggestion index"):
        ui.run()


def test_ui_rejects_invalid_suggestion_set() -> None:
    with pytest.raises(TypeError, match="CommitSuggestionSet"):
        CommitSuggestionTerminalUI(None)  # type: ignore[arg-type]


def test_ui_escapes_non_printable_characters_for_display() -> None:
    message = "feat(auth): add login\x1b[31m"
    suggestions = CommitSuggestionSet(
        suggestions=(
            CommitSuggestion(message=message),
            CommitSuggestion(message="fix(auth): handle errors"),
            CommitSuggestion(message="test(auth): cover login"),
        )
    )

    output = StringIO()
    console = Console(file=output, force_terminal=False)

    prompt = Mock()
    prompt.return_value.ask.return_value = 0

    ui = CommitSuggestionTerminalUI(
        suggestions=suggestions,
        console=console,
        select_prompt=prompt,
    )

    result = ui.run()

    choices = prompt.call_args.kwargs["choices"]

    assert result == message
    assert "\x1b" not in choices[0].title
    assert "\\u001b" in choices[0].title
