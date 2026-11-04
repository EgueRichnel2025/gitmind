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


def test_git_command_error_inherits_from_git_runner_error() -> None:
    from pathlib import Path

    from gitmind.core.git.errors import GitCommandError
    from gitmind.core.git.models import GitCommandResult

    result = GitCommandResult(
        args=("status",),
        cwd=Path("/project"),
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
        duration_seconds=0.03,
    )

    error = GitCommandError(result)

    assert isinstance(error, GitRunnerError)
    assert isinstance(error, RuntimeError)


def test_git_command_error_preserves_execution_metadata() -> None:
    from pathlib import Path

    from gitmind.core.git.errors import GitCommandError
    from gitmind.core.git.models import GitCommandResult

    result = GitCommandResult(
        args=("diff", "--cached"),
        cwd=Path("/project"),
        returncode=1,
        stdout="",
        stderr="permission denied",
        duration_seconds=0.05,
    )

    error = GitCommandError(result)

    assert error.result is result
    assert error.command == ("diff", "--cached")
    assert error.cwd == Path("/project")
    assert error.returncode == 1
    assert error.stdout == ""
    assert error.stderr == "permission denied"


def test_git_command_error_has_informative_message() -> None:
    from pathlib import Path

    from gitmind.core.git.errors import GitCommandError
    from gitmind.core.git.models import GitCommandResult

    result = GitCommandResult(
        args=("status",),
        cwd=Path("/project"),
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
        duration_seconds=0.02,
    )

    error = GitCommandError(result)
    message = str(error)

    assert "git status" in message
    assert "128" in message
    assert str(Path("/project")) in message
    assert "fatal: not a git repository" in message


def test_git_status_parse_error_inherits_from_git_runner_error() -> None:
    from gitmind.core.git.errors import GitStatusParseError

    error = GitStatusParseError("Invalid status entry")

    assert isinstance(error, GitRunnerError)
    assert isinstance(error, RuntimeError)


def test_git_status_parse_error_preserves_details() -> None:
    from gitmind.core.git.errors import GitStatusParseError

    error = GitStatusParseError(
        reason="Invalid status entry",
        entry="invalid-record",
    )

    assert error.reason == "Invalid status entry"
    assert error.entry == "invalid-record"


def test_git_status_parse_error_has_informative_message() -> None:
    from gitmind.core.git.errors import GitStatusParseError

    error = GitStatusParseError(
        reason="Missing filename",
        entry="M ",
    )

    assert "Unable to parse Git status output" in str(error)
    assert "Missing filename" in str(error)
    assert "M " in str(error)


def test_git_repository_not_found_error_preserves_path() -> None:
    from pathlib import Path

    from gitmind.core.git.errors import GitRepositoryNotFoundError

    path = Path("/project")
    error = GitRepositoryNotFoundError(path)

    assert isinstance(error, GitRunnerError)
    assert error.path == path
    assert "/project" in str(error)
