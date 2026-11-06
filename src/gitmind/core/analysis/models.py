"""Immutable data models for GitMind file analysis."""

from dataclasses import dataclass

from gitmind.core.git.status_models import GitFileStatus


@dataclass(frozen=True, slots=True)
class FileAnalysis:
    """Represent the analysis data collected for a single Git file.

    The content represents the current working-tree version of the file.
    It is None when the content is unavailable, for example for deleted
    or binary files.

    Diffs are kept separate to distinguish staged and unstaged changes.
    """

    git_file: GitFileStatus
    staged_diff: str = ""
    unstaged_diff: str = ""
    content: str | None = None
    is_binary: bool = False
    content_truncated: bool = False
    staged_diff_truncated: bool = False
    unstaged_diff_truncated: bool = False
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.git_file, GitFileStatus):
            raise TypeError("git_file must be a GitFileStatus instance.")

        if not isinstance(self.staged_diff, str):
            raise TypeError("staged_diff must be a string.")

        if not isinstance(self.unstaged_diff, str):
            raise TypeError("unstaged_diff must be a string.")

        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("content must be a string or None.")

        boolean_fields = (
            "is_binary",
            "content_truncated",
            "staged_diff_truncated",
            "unstaged_diff_truncated",
        )

        for field_name in boolean_fields:
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean.")

        if self.is_binary and self.content is not None:
            raise ValueError("Binary files cannot contain decoded text content.")

        if self.content_truncated and self.content is None:
            raise ValueError("Truncated content must not be None.")

        if self.size_bytes is not None:
            if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
                raise TypeError("size_bytes must be an integer or None.")

            if self.size_bytes < 0:
                raise ValueError("size_bytes cannot be negative.")

    @property
    def path(self) -> str:
        """Return the repository-relative file path."""
        return self.git_file.path

    @property
    def original_path(self) -> str | None:
        """Return the original path for renamed or copied files."""
        return self.git_file.original_path

    @property
    def status_code(self) -> str:
        """Return the two-character Git status code."""
        return self.git_file.status_code

    @property
    def has_staged_diff(self) -> bool:
        """Return whether staged modifications have a diff."""
        return bool(self.staged_diff)

    @property
    def has_unstaged_diff(self) -> bool:
        """Return whether unstaged modifications have a diff."""
        return bool(self.unstaged_diff)

    @property
    def has_diff(self) -> bool:
        """Return whether either staged or unstaged changes have a diff."""
        return self.has_staged_diff or self.has_unstaged_diff

    @property
    def diff_truncated(self) -> bool:
        """Return whether at least one diff has been truncated."""
        return self.staged_diff_truncated or self.unstaged_diff_truncated

    @property
    def has_content(self) -> bool:
        """Return whether decoded text content is available."""
        return self.content is not None


@dataclass(frozen=True, slots=True)
class FileAnalysisSnapshot:
    """Represent an immutable collection of file analysis results."""

    files: tuple[FileAnalysis, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.files, tuple):
            raise TypeError("files must be a tuple of FileAnalysis instances.")

        if any(not isinstance(file, FileAnalysis) for file in self.files):
            raise TypeError("All files must be FileAnalysis instances.")

        paths = [file.path for file in self.files]

        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate file paths are not allowed in an analysis.")

    @property
    def file_count(self) -> int:
        """Return the number of analyzed files."""
        return len(self.files)

    @property
    def is_empty(self) -> bool:
        """Return whether the analysis contains no files."""
        return not self.files

    @property
    def paths(self) -> tuple[str, ...]:
        """Return analyzed file paths while preserving their original order."""
        return tuple(file.path for file in self.files)

    @property
    def staged_diff_count(self) -> int:
        """Return the number of files with staged diffs."""
        return sum(file.has_staged_diff for file in self.files)

    @property
    def unstaged_diff_count(self) -> int:
        """Return the number of files with unstaged diffs."""
        return sum(file.has_unstaged_diff for file in self.files)

    @property
    def binary_count(self) -> int:
        """Return the number of binary files."""
        return sum(file.is_binary for file in self.files)

    @property
    def content_truncated_count(self) -> int:
        """Return the number of files with truncated content."""
        return sum(file.content_truncated for file in self.files)

    @property
    def diff_truncated_count(self) -> int:
        """Return the number of files with at least one truncated diff."""
        return sum(file.diff_truncated for file in self.files)

    @property
    def has_diffs(self) -> bool:
        """Return whether at least one file contains a diff."""
        return any(file.has_diff for file in self.files)
