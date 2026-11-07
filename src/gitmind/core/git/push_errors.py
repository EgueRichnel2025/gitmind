"""Exceptions for Git push operations."""


class GitPushError(RuntimeError):
    """Base exception for Git push operations."""


class GitPushRemoteNotFoundError(GitPushError):
    """Raised when the configured remote does not exist."""

    def __init__(self, remote_name: str) -> None:
        self.remote_name = remote_name
        super().__init__(f"Git remote does not exist: {remote_name}")


class GitPushDetachedHeadError(GitPushError):
    """Raised when a push is attempted from a detached HEAD."""

    def __init__(self) -> None:
        super().__init__("Cannot push from a detached HEAD. Check out a branch first.")
