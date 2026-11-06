"""Tests for commit suggestion data models."""

from dataclasses import FrozenInstanceError

import pytest

from gitmind.core.ai import (
    CommitSuggestion,
    CommitSuggestionSet,
)


def make_suggestion(message: str) -> CommitSuggestion:
    return CommitSuggestion(message=message)


def make_suggestion_set() -> CommitSuggestionSet:
    return CommitSuggestionSet(
        suggestions=(
            make_suggestion("feat(auth): implement authentication"),
            make_suggestion("refactor(auth): simplify authentication flow"),
            make_suggestion("test(auth): add authentication tests"),
        )
    )


def test_commit_suggestion_accepts_valid_message() -> None:
    suggestion = make_suggestion("feat(auth): implement authentication")

    assert suggestion.message == "feat(auth): implement authentication"


@pytest.mark.parametrize(
    "message",
    [
        "",
        " ",
        "   ",
        "\n",
        "\n\n",
    ],
)
def test_commit_suggestion_rejects_empty_messages(message: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        make_suggestion(message)


@pytest.mark.parametrize(
    "message",
    [
        " feat(auth): add login",
        "feat(auth): add login ",
    ],
)
def test_commit_suggestion_rejects_surrounding_whitespace(
    message: str,
) -> None:
    with pytest.raises(ValueError, match="surrounding whitespace"):
        make_suggestion(message)


@pytest.mark.parametrize(
    "message",
    [
        "feat(auth): add login\nfix(auth): handle errors",
        "feat(auth): add login\rfix(auth): handle errors",
    ],
)
def test_commit_suggestion_rejects_multiline_messages(
    message: str,
) -> None:
    with pytest.raises(ValueError, match="exactly one line"):
        make_suggestion(message)


def test_commit_suggestion_rejects_nul_character() -> None:
    with pytest.raises(ValueError, match="NUL"):
        make_suggestion("feat(auth): add\0login")


def test_commit_suggestion_rejects_non_string_message() -> None:
    with pytest.raises(TypeError, match="message must be a string"):
        CommitSuggestion(message=123)  # type: ignore[arg-type]


def test_commit_suggestion_is_immutable() -> None:
    suggestion = make_suggestion("feat(auth): add login")

    with pytest.raises(FrozenInstanceError):
        suggestion.message = "fix(auth): add login"  # type: ignore[misc]


def test_suggestion_set_accepts_exactly_three_messages() -> None:
    result = make_suggestion_set()

    assert len(result.suggestions) == 3
    assert len(result.messages) == 3


def test_suggestion_set_preserves_message_order() -> None:
    result = make_suggestion_set()

    assert result.messages == (
        "feat(auth): implement authentication",
        "refactor(auth): simplify authentication flow",
        "test(auth): add authentication tests",
    )


@pytest.mark.parametrize(
    "suggestions",
    [
        (),
        (make_suggestion("feat: add feature"),),
        (
            make_suggestion("feat: add feature"),
            make_suggestion("fix: correct bug"),
        ),
        (
            make_suggestion("feat: add feature"),
            make_suggestion("fix: correct bug"),
            make_suggestion("docs: update documentation"),
            make_suggestion("test: add tests"),
        ),
    ],
)
def test_suggestion_set_rejects_invalid_number_of_suggestions(
    suggestions: tuple[CommitSuggestion, ...],
) -> None:
    with pytest.raises(ValueError, match="Exactly three"):
        CommitSuggestionSet(suggestions=suggestions)


def test_suggestion_set_rejects_non_tuple_suggestions() -> None:
    with pytest.raises(TypeError, match="must be a tuple"):
        CommitSuggestionSet(
            suggestions=[
                make_suggestion("feat: add feature"),
                make_suggestion("fix: correct bug"),
                make_suggestion("test: add tests"),
            ]  # type: ignore[arg-type]
        )


def test_suggestion_set_rejects_invalid_suggestion_instances() -> None:
    with pytest.raises(TypeError, match="CommitSuggestion instances"):
        CommitSuggestionSet(
            suggestions=(
                make_suggestion("feat: add feature"),
                "fix: correct bug",
                make_suggestion("test: add tests"),
            )  # type: ignore[arg-type]
        )


def test_suggestion_set_rejects_duplicate_messages() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        CommitSuggestionSet(
            suggestions=(
                make_suggestion("feat(auth): add login"),
                make_suggestion("fix(auth): handle errors"),
                make_suggestion("FEAT(AUTH): ADD LOGIN"),
            )
        )


def test_suggestion_set_is_immutable() -> None:
    result = make_suggestion_set()

    with pytest.raises(FrozenInstanceError):
        result.suggestions = ()  # type: ignore[misc]
