"""Tests for Git status data models."""

import pytest

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot


def test_file_status_preserves_both_status_columns() -> None:
    file = GitFileStatus(
        path="src/auth.py",
        index_status="M",
        worktree_status="M",
    )

    assert file.status_code == "MM"
    assert file.is_staged
    assert file.is_unstaged


def test_staged_file_is_not_marked_as_unstaged() -> None:
    file = GitFileStatus(
        path="src/auth.py",
        index_status="M",
        worktree_status=" ",
    )

    assert file.is_staged
    assert not file.is_unstaged


def test_unstaged_file_is_not_marked_as_staged() -> None:
    file = GitFileStatus(
        path="src/auth.py",
        index_status=" ",
        worktree_status="M",
    )

    assert not file.is_staged
    assert file.is_unstaged


def test_untracked_file_is_not_treated_as_staged() -> None:
    file = GitFileStatus(
        path="src/new_module.py",
        index_status="?",
        worktree_status="?",
    )

    assert file.is_untracked
    assert file.is_added
    assert not file.is_staged
    assert file.is_unstaged


def test_deleted_file_is_identified() -> None:
    file = GitFileStatus(
        path="src/old_module.py",
        index_status="D",
        worktree_status=" ",
    )

    assert file.is_deleted


def test_renamed_file_preserves_original_path() -> None:
    file = GitFileStatus(
        path="src/new_name.py",
        index_status="R",
        worktree_status=" ",
        original_path="src/old_name.py",
    )

    assert file.is_renamed
    assert file.original_path == "src/old_name.py"


def test_invalid_untracked_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="Untracked files"):
        GitFileStatus(
            path="new_file.py",
            index_status="?",
            worktree_status=" ",
        )


def test_invalid_original_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="Original path"):
        GitFileStatus(
            path="src/auth.py",
            index_status="M",
            worktree_status=" ",
            original_path="src/old_auth.py",
        )


def test_status_snapshot_calculates_counts() -> None:
    snapshot = GitStatusSnapshot(
        files=(
            GitFileStatus("src/staged.py", "M", " "),
            GitFileStatus("src/unstaged.py", " ", "M"),
            GitFileStatus("src/untracked.py", "?", "?"),
            GitFileStatus("src/both.py", "M", "M"),
        )
    )

    assert snapshot.file_count == 4
    assert snapshot.staged_count == 2
    assert snapshot.unstaged_count == 3
    assert snapshot.untracked_count == 1
    assert not snapshot.is_clean


def test_empty_snapshot_is_clean() -> None:
    snapshot = GitStatusSnapshot(files=())

    assert snapshot.file_count == 0
    assert snapshot.is_clean
    assert snapshot.staged_count == 0
    assert snapshot.unstaged_count == 0
