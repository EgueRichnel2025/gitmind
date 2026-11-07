"""Custom exceptions for Git commit operations."""


class GitCommitError(RuntimeError):
    """Base exception for Git commit operations."""


class EmptyGitCommitSelectionError(GitCommitError):
    """Raised when a commit is requested without selected files."""

    def __init__(self) -> None:
        super().__init__("Cannot create a commit without selected files.")


class InvalidGitCommitMessageError(GitCommitError):
    """Raised when a commit message is invalid."""


class GitCommitSelectionNotStagedError(GitCommitError):
    """Raised when a selected file no longer has staged changes."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Selected file is not staged: {path}")


class GitCommitSelectionHasUnstagedChangesError(GitCommitError):
    """Raised when a selected file changed after staging."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Selected file has additional unstaged changes: {path}")


class GitCommitSelectionUnmergedError(GitCommitError):
    """Raised when a selected file has unresolved merge conflicts."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Selected file has unresolved merge conflicts: {path}")


class UnsafeGitCommitPathError(GitCommitError):
    """Raised when a selected path is unsafe for a Git operation."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Unsafe selected file path {path!r}: {reason}")
