"""Tests for the Git command runner."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.git.errors import (
    GitCommandError,
    GitNotFoundError,
    GitTimeoutError,
)
from gitmind.core.git.runner import GitRunner


def test_runner_resolves_git_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gitmind.core.git.runner.shutil.which",
        lambda executable: "/usr/bin/git",
    )

    runner = GitRunner()

    assert runner.executable_path == "/usr/bin/git"


def test_runner_raises_when_git_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.git.runner.shutil.which",
        lambda executable: None,
    )

    with pytest.raises(GitNotFoundError):
        GitRunner()


def test_runner_rejects_invalid_default_timeout() -> None:
    with pytest.raises(ValueError, match="positive finite"):
        GitRunner(default_timeout_seconds=0)


def test_run_captures_command_output_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        assert command[-2:] == ["--version"] or command[-1] == "version"
        assert kwargs["shell"] is False
        assert kwargs["capture_output"] is True

        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="git version 2.51.1",
            stderr="",
        )

    monkeypatch.setattr(
        "gitmind.core.git.runner.shutil.which",
        lambda executable: "git",
    )
    monkeypatch.setattr(
        "gitmind.core.git.runner.subprocess.run",
        fake_run,
    )

    runner = GitRunner()
    result = runner.run("version", cwd=tmp_path)

    assert result.succeeded
    assert result.stdout == "git version 2.51.1"
    assert result.stderr == ""
    assert result.cwd == tmp_path.resolve()
    assert result.args == ("version",)


def test_run_raises_git_command_error_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.git.runner.shutil.which",
        lambda executable: "git",
    )
    monkeypatch.setattr(
        "gitmind.core.git.runner.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        ),
    )

    runner = GitRunner()

    with pytest.raises(GitCommandError) as error:
        runner.run("status", cwd=tmp_path)

    assert error.value.returncode == 128
    assert "not a git repository" in str(error.value)


def test_run_can_return_failed_result_when_check_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.git.runner.shutil.which",
        lambda executable: "git",
    )
    monkeypatch.setattr(
        "gitmind.core.git.runner.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="expected non-zero result",
        ),
    )

    runner = GitRunner()
    result = runner.run("diff", "--quiet", cwd=tmp_path, check=False)

    assert not result.succeeded
    assert result.returncode == 1


def test_run_raises_git_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd="git status",
            timeout=2.0,
        )

    monkeypatch.setattr(
        "gitmind.core.git.runner.shutil.which",
        lambda executable: "git",
    )
    monkeypatch.setattr(
        "gitmind.core.git.runner.subprocess.run",
        fake_run,
    )

    runner = GitRunner()

    with pytest.raises(GitTimeoutError) as error:
        runner.run("status", cwd=tmp_path, timeout_seconds=2.0)

    assert error.value.timeout_seconds == 2.0
    assert error.value.command == ("status",)


def test_run_rejects_empty_command() -> None:
    runner = GitRunner()

    with pytest.raises(ValueError, match="At least one Git argument"):
        runner.run()


def test_run_rejects_non_string_arguments() -> None:
    runner = GitRunner()

    with pytest.raises(TypeError, match="must be strings"):
        runner.run("status", 123)  # type: ignore[arg-type]
