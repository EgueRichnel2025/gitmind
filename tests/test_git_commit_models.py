"""Tests for Git commit models and errors."""

import pytest

from gitmind.core.git.commit_errors import (
    EmptyGitCommitSelectionError,
    GitCommitError,
    GitCommitSelectionHasUnstagedChangesError,
    GitCommitSelectionNotStagedError,
    InvalidGitCommitMessageError,
)
from gitmind.core.git.commit_models import GitCommitResult

VALID_HASH = "a" * 40


def test_commit_result_stores_commit_information() -> None:
    result = GitCommitResult(
        commit_hash=VALID_HASH,
        message="feat(auth): add authentication",
        committed_paths=("src/auth.py", "tests/test_auth.py"),
    )

    assert result.commit_hash == VALID_HASH
    assert result.message == "feat(auth): add authentication"
    assert result.committed_paths == (
        "src/auth.py",
        "tests/test_auth.py",
    )


def test_commit_result_exposes_committed_count() -> None:
    result = GitCommitResult(
        commit_hash=VALID_HASH,
        message="feat: add feature",
        committed_paths=("app.py", "tests.py"),
    )

    assert result.committed_count == 2


@pytest.mark.parametrize("commit_hash", ["", "abc", "g" * 40, "a" * 41])
def test_commit_result_rejects_invalid_hash(commit_hash: str) -> None:
    with pytest.raises(ValueError):
        GitCommitResult(
            commit_hash=commit_hash,
            message="feat: add feature",
            committed_paths=("app.py",),
        )


def test_commit_result_accepts_sha256_hash() -> None:
    result = GitCommitResult(
        commit_hash="b" * 64,
        message="feat: add feature",
        committed_paths=("app.py",),
    )

    assert len(result.commit_hash) == 64


def test_commit_result_rejects_empty_message() -> None:
    with pytest.raises(ValueError, match="message cannot be empty"):
        GitCommitResult(
            commit_hash=VALID_HASH,
            message=" ",
            committed_paths=("app.py",),
        )


@pytest.mark.parametrize("message", ["feat: add feature\nextra", "feat: add feature\r"])
def test_commit_result_rejects_multiline_message(message: str) -> None:
    with pytest.raises(ValueError, match="single line"):
        GitCommitResult(
            commit_hash=VALID_HASH,
            message=message,
            committed_paths=("app.py",),
        )


def test_commit_result_rejects_surrounding_whitespace() -> None:
    with pytest.raises(ValueError, match="surrounding whitespace"):
        GitCommitResult(
            commit_hash=VALID_HASH,
            message=" feat: add feature ",
            committed_paths=("app.py",),
        )


def test_commit_result_rejects_empty_paths() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        GitCommitResult(
            commit_hash=VALID_HASH,
            message="feat: add feature",
            committed_paths=(),
        )


def test_commit_result_rejects_duplicate_paths() -> None:
    with pytest.raises(ValueError, match="Duplicate committed paths"):
        GitCommitResult(
            commit_hash=VALID_HASH,
            message="feat: add feature",
            committed_paths=("app.py", "app.py"),
        )


def test_commit_error_hierarchy() -> None:
    assert issubclass(EmptyGitCommitSelectionError, GitCommitError)
    assert issubclass(InvalidGitCommitMessageError, GitCommitError)
    assert issubclass(GitCommitSelectionNotStagedError, GitCommitError)
    assert issubclass(
        GitCommitSelectionHasUnstagedChangesError,
        GitCommitError,
    )


def test_commit_selection_not_staged_error_preserves_path() -> None:
    error = GitCommitSelectionNotStagedError("app.py")

    assert error.path == "app.py"
    assert "app.py" in str(error)


def test_commit_selection_unstaged_error_preserves_path() -> None:
    error = GitCommitSelectionHasUnstagedChangesError("app.py")

    assert error.path == "app.py"
    assert "unstaged" in str(error)


def test_empty_commit_selection_error_message() -> None:
    error = EmptyGitCommitSelectionError()

    assert "without selected files" in str(error)
