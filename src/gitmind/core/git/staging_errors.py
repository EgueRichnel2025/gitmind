"""Custom exceptions for Git staging operations."""


class GitStagingError(RuntimeError):
    """Base exception for Git staging operations."""


class EmptyGitStagingSelectionError(GitStagingError):
    """Raised when staging is requested without selected files."""

    def __init__(self) -> None:
        super().__init__("Cannot stage files because the selection is empty.")


class UnsafeGitPathError(GitStagingError):
    """Raised when a selected path is unsafe for a staging operation."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason

        super().__init__(f"Unsafe Git path {path!r}: {reason}")
