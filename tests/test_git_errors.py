"""Tests for Git runner exceptions."""

from gitmind.core.git.errors import GitNotFoundError, GitRunnerError


def test_git_runner_error_is_a_runtime_error() -> None:
    error = GitRunnerError("Git runner failed")

    assert isinstance(error, RuntimeError)
    assert str(error) == "Git runner failed"


def test_git_not_found_error_inherits_from_git_runner_error() -> None:
    error = GitNotFoundError()

    assert isinstance(error, GitRunnerError)
    assert isinstance(error, RuntimeError)


def test_git_not_found_error_preserves_executable_name() -> None:
    error = GitNotFoundError("git.exe")

    assert error.executable == "git.exe"
    assert "git.exe" in str(error)
    assert "PATH" in str(error)


def test_git_timeout_error_inherits_from_git_runner_error() -> None:
    from pathlib import Path

    from gitmind.core.git.errors import GitTimeoutError

    error = GitTimeoutError(
        command=("git", "status"),
        cwd=Path("/project"),
        timeout_seconds=10.0,
    )

    assert isinstance(error, GitRunnerError)
    assert isinstance(error, RuntimeError)


def test_git_timeout_error_preserves_execution_metadata() -> None:
    from pathlib import Path

    from gitmind.core.git.errors import GitTimeoutError

    cwd = Path("/project")
    command = ("git", "diff", "--cached")

    error = GitTimeoutError(
        command=command,
        cwd=cwd,
        timeout_seconds=5.0,
    )

    assert error.command == command
    assert error.cwd == cwd
    assert error.timeout_seconds == 5.0


def test_git_timeout_error_has_informative_message() -> None:
    from pathlib import Path

    from gitmind.core.git.errors import GitTimeoutError

    error = GitTimeoutError(
        command=("git", "status", "--short"),
        cwd=Path("/project"),
        timeout_seconds=3.5,
    )

    assert "git status --short" in str(error)
    assert "3.5 seconds" in str(error)
    assert str(Path("/project")) in str(error)
