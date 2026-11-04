"""Custom exceptions for Git command execution."""


class GitRunnerError(RuntimeError):
    """Base exception for Git runner errors."""


class GitNotFoundError(GitRunnerError):
    """Raised when the Git executable cannot be found."""

    def __init__(self, executable: str = "git") -> None:
        self.executable = executable

        super().__init__(
            f"Git executable '{executable}' was not found. "
            "Make sure Git is installed and available in PATH."
        )
