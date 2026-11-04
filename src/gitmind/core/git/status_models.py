"""Data models for Git working tree status."""

from dataclasses import dataclass

_VALID_STATUS_CODES = frozenset(" MADRCUT?!")


@dataclass(frozen=True, slots=True)
class GitFileStatus:
    """Represent the Git status of a single file."""

    path: str
    index_status: str
    worktree_status: str
    original_path: str | None = None

    def __post_init__(self) -> None:
        if not self.path or "\0" in self.path:
            raise ValueError("File path cannot be empty or contain NUL characters.")

        if self.index_status not in _VALID_STATUS_CODES:
            raise ValueError(f"Invalid index status: {self.index_status!r}")

        if self.worktree_status not in _VALID_STATUS_CODES:
            raise ValueError(f"Invalid worktree status: {self.worktree_status!r}")

        if (self.index_status == "?") != (self.worktree_status == "?"):
            raise ValueError("Untracked files must have the status '??'.")

        if (self.index_status == "!") != (self.worktree_status == "!"):
            raise ValueError("Ignored files must have the status '!!'.")

        if self.original_path is not None and not (self.is_renamed or self.is_copied):
            raise ValueError("Original path is only valid for renamed or copied files.")

        if (self.is_renamed or self.is_copied) and self.original_path is None:
            raise ValueError("Renamed or copied files must have an original path.")

    @property
    def status_code(self) -> str:
        """Return the two-character Git status code."""
        return f"{self.index_status}{self.worktree_status}"

    @property
    def is_staged(self) -> bool:
        """Return whether the file has changes in the index."""
        return self.index_status not in {" ", "?", "!"}

    @property
    def is_unstaged(self) -> bool:
        """Return whether the file has working tree changes."""
        return self.worktree_status not in {" ", "!"}

    @property
    def is_untracked(self) -> bool:
        """Return whether the file is not tracked by Git."""
        return self.status_code == "??"

    @property
    def is_ignored(self) -> bool:
        """Return whether the file is ignored by Git."""
        return self.status_code == "!!"

    @property
    def is_modified(self) -> bool:
        """Return whether the file has a modification."""
        return "M" in self.status_code

    @property
    def is_added(self) -> bool:
        """Return whether the file has been added."""
        return "A" in self.status_code or self.is_untracked

    @property
    def is_deleted(self) -> bool:
        """Return whether the file has been deleted."""
        return "D" in self.status_code

    @property
    def is_renamed(self) -> bool:
        """Return whether the file has been renamed."""
        return "R" in self.status_code

    @property
    def is_copied(self) -> bool:
        """Return whether the file has been copied."""
        return "C" in self.status_code

    @property
    def is_type_changed(self) -> bool:
        """Return whether the file type has changed."""
        return "T" in self.status_code

    @property
    def is_unmerged(self) -> bool:
        """Return whether the file has unresolved merge changes."""
        return "U" in self.status_code


@dataclass(frozen=True, slots=True)
class GitStatusSnapshot:
    """Represent a snapshot of all reported Git file changes."""

    files: tuple[GitFileStatus, ...]

    @property
    def file_count(self) -> int:
        """Return the number of reported files."""
        return len(self.files)

    @property
    def is_clean(self) -> bool:
        """Return whether the snapshot contains no file changes."""
        return not self.files

    @property
    def staged_count(self) -> int:
        """Return the number of files with staged changes."""
        return sum(file.is_staged for file in self.files)

    @property
    def unstaged_count(self) -> int:
        """Return the number of files with working tree changes."""
        return sum(file.is_unstaged for file in self.files)

    @property
    def untracked_count(self) -> int:
        """Return the number of untracked files."""
        return sum(file.is_untracked for file in self.files)
