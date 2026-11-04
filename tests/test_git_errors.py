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
