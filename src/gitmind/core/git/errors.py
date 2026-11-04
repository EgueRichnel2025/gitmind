"""Custom exceptions for Git command execution."""

from pathlib import Path


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


class GitTimeoutError(GitRunnerError):
    """Raised when a Git command exceeds its execution timeout."""

    def __init__(
        self,
        command: tuple[str, ...],
        cwd: Path,
        timeout_seconds: float,
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds

        command_text = " ".join(command)

        super().__init__(
            f"Git command '{command_text}' timed out after {timeout_seconds:g} seconds in '{cwd}'."
        )
