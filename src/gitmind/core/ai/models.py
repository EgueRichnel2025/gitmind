"""Immutable data models for commit message suggestions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommitSuggestion:
    """Represent one proposed Git commit message."""

    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.message, str):
            raise TypeError("message must be a string.")

        if not self.message or not self.message.strip():
            raise ValueError("message cannot be empty.")

        if self.message != self.message.strip():
            raise ValueError("message cannot contain surrounding whitespace.")

        if "\n" in self.message or "\r" in self.message:
            raise ValueError("message must contain exactly one line.")

        if "\0" in self.message:
            raise ValueError("message cannot contain NUL characters.")


@dataclass(frozen=True, slots=True)
class CommitSuggestionSet:
    """Represent exactly three distinct commit message suggestions."""

    suggestions: tuple[CommitSuggestion, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.suggestions, tuple):
            raise TypeError("suggestions must be a tuple.")

        if len(self.suggestions) != 3:
            raise ValueError("Exactly three commit suggestions are required.")

        if any(not isinstance(suggestion, CommitSuggestion) for suggestion in self.suggestions):
            raise TypeError("All suggestions must be CommitSuggestion instances.")

        normalized_messages = [suggestion.message.casefold() for suggestion in self.suggestions]

        if len(normalized_messages) != len(set(normalized_messages)):
            raise ValueError("Duplicate commit suggestions are not allowed.")

    @property
    def messages(self) -> tuple[str, ...]:
        """Return the three messages while preserving their original order."""
        return tuple(suggestion.message for suggestion in self.suggestions)
