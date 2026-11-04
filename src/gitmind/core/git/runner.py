"""Safe subprocess-based Git command execution."""

import math
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

from gitmind.core.git.errors import (
    GitCommandError,
    GitNotFoundError,
    GitTimeoutError,
)
from gitmind.core.git.models import GitCommandResult


class GitRunner:
    """Execute Git commands and capture their results."""

    def __init__(
        self,
        executable: str = "git",
        default_timeout_seconds: float = 10.0,
    ) -> None:
        if not executable.strip():
            raise ValueError("Git executable cannot be empty.")

        self._executable = shutil.which(executable)

        if self._executable is None:
            raise GitNotFoundError(executable)

        self._default_timeout_seconds = self._validate_timeout(default_timeout_seconds)

    @property
    def executable_path(self) -> str:
        """Return the resolved Git executable path."""
        return self._executable

    @staticmethod
    def _validate_timeout(timeout_seconds: float) -> float:
        """Validate and normalize a timeout value."""
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("Timeout must be a positive finite number.")

        return float(timeout_seconds)

    def run(
        self,
        *args: str,
        cwd: str | Path | None = None,
        timeout_seconds: float | None = None,
        check: bool = True,
    ) -> GitCommandResult:
        """Execute a Git command and return its captured result."""
        if not args:
            raise ValueError("At least one Git argument is required.")

        if any(not isinstance(arg, str) for arg in args):
            raise TypeError("All Git arguments must be strings.")

        if not args[0]:
            raise ValueError("Git subcommand cannot be empty.")

        timeout = (
            self._default_timeout_seconds
            if timeout_seconds is None
            else self._validate_timeout(timeout_seconds)
        )

        working_directory = Path.cwd() if cwd is None else Path(cwd)

        if not working_directory.exists():
            raise FileNotFoundError(f"Git working directory does not exist: {working_directory}")

        if not working_directory.is_dir():
            raise NotADirectoryError(
                f"Git working directory is not a directory: {working_directory}"
            )

        working_directory = working_directory.resolve()
        command = [self._executable, *args]

        start_time = perf_counter()

        try:
            completed = subprocess.run(
                command,
                cwd=working_directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise GitNotFoundError(self._executable) from exc
        except subprocess.TimeoutExpired as exc:
            raise GitTimeoutError(
                command=tuple(args),
                cwd=working_directory,
                timeout_seconds=timeout,
            ) from exc

        duration = perf_counter() - start_time

        result = GitCommandResult(
            args=tuple(args),
            cwd=working_directory,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=duration,
        )

        if check and not result.succeeded:
            raise GitCommandError(result)

        return result
