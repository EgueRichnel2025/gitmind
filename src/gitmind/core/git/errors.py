"""Custom exceptions for Git command execution."""

from pathlib import Path

from gitmind.core.git.models import GitCommandResult


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


class GitCommandError(GitRunnerError):
    """Raised when a Git command returns a non-zero exit code."""

    def __init__(self, result: GitCommandResult) -> None:
        self.result = result
        self.command = result.args
        self.cwd = result.cwd
        self.returncode = result.returncode
        self.stdout = result.stdout
        self.stderr = result.stderr

        command_text = " ".join(result.args)
        details = result.stderr.strip() or result.stdout.strip()

        message = (
            f"Git command 'git {command_text}' failed with exit code "
            f"{result.returncode} in '{result.cwd}'."
        )

        if details:
            message = f"{message}\n{details}"

        super().__init__(message)


class GitStatusParseError(GitRunnerError):
    """Raised when Git status output cannot be parsed."""

    def __init__(self, reason: str, entry: str | None = None) -> None:
        self.reason = reason
        self.entry = entry

        message = f"Unable to parse Git status output: {reason}"

        if entry is not None:
            message = f"{message} Entry: {entry!r}"

        super().__init__(message)
