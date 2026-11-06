"""Immutable data models for Git file differences."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileDiff:
    """Represent staged and unstaged differences for one file."""

    path: str
    staged_diff: str = ""
    unstaged_diff: str = ""
    staged_diff_truncated: bool = False
    unstaged_diff_truncated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.path, str):
            raise TypeError("path must be a string.")

        if not self.path or "\0" in self.path:
            raise ValueError("path cannot be empty or contain NUL characters.")

        for field_name in ("staged_diff", "unstaged_diff"):
            if not isinstance(getattr(self, field_name), str):
                raise TypeError(f"{field_name} must be a string.")

        for field_name in (
            "staged_diff_truncated",
            "unstaged_diff_truncated",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if self.staged_diff_truncated and not self.staged_diff:
            raise ValueError("A truncated staged diff cannot be empty.")

        if self.unstaged_diff_truncated and not self.unstaged_diff:
            raise ValueError("A truncated unstaged diff cannot be empty.")

    @property
    def has_staged_diff(self) -> bool:
        """Return whether staged changes contain a diff."""
        return bool(self.staged_diff)

    @property
    def has_unstaged_diff(self) -> bool:
        """Return whether unstaged changes contain a diff."""
        return bool(self.unstaged_diff)

    @property
    def has_diff(self) -> bool:
        """Return whether either staged or unstaged changes exist."""
        return self.has_staged_diff or self.has_unstaged_diff

    @property
    def is_truncated(self) -> bool:
        """Return whether at least one diff has been truncated."""
        return self.staged_diff_truncated or self.unstaged_diff_truncated
