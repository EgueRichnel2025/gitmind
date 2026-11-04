"""Tests for Git command result models."""

from pathlib import Path

from gitmind.core.git.models import GitCommandResult


def test_successful_command_result() -> None:
    result = GitCommandResult(
        args=("status", "--short"),
        cwd=Path("/project"),
        returncode=0,
        stdout=" M src/main.py",
        stderr="",
        duration_seconds=0.05,
    )

    assert result.succeeded is True
    assert result.returncode == 0
    assert result.stdout == " M src/main.py"


def test_failed_command_result() -> None:
    result = GitCommandResult(
        args=("invalid-command",),
        cwd=Path("/project"),
        returncode=1,
        stdout="",
        stderr="git: 'invalid-command' is not a git command",
        duration_seconds=0.02,
    )

    assert result.succeeded is False
    assert result.returncode == 1
    assert "invalid-command" in result.stderr


def test_command_result_preserves_execution_metadata() -> None:
    result = GitCommandResult(
        args=("diff", "--cached"),
        cwd=Path("/project"),
        returncode=0,
        stdout="diff output",
        stderr="",
        duration_seconds=0.12,
    )

    assert result.args == ("diff", "--cached")
    assert result.cwd == Path("/project")
    assert result.duration_seconds == 0.12
