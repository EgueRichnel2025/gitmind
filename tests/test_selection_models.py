"""Tests for GitMind file selection models."""

import pytest

from gitmind.core.git.status_models import GitFileStatus
from gitmind.core.selection.models import (
    FileSelectionSnapshot,
    SelectableFile,
)


def create_selectable_file(
    path: str,
    selected: bool = False,
) -> SelectableFile:
    """Create a selectable file for testing."""
    git_file = GitFileStatus(
        path=path,
        index_status=" ",
        worktree_status="M",
    )

    return SelectableFile(
        git_file=git_file,
        selected=selected,
    )


def test_selectable_file_defaults_to_unselected() -> None:
    file = create_selectable_file("src/auth.py")

    assert file.selected is False
    assert file.path == "src/auth.py"


def test_selectable_file_preserves_git_metadata() -> None:
    file = create_selectable_file("src/payment.py", selected=True)

    assert file.selected is True
    assert file.git_file.status_code == " M"
    assert file.git_file.is_unstaged


def test_selection_snapshot_calculates_file_counts() -> None:
    snapshot = FileSelectionSnapshot(
        files=(
            create_selectable_file("src/auth.py", True),
            create_selectable_file("src/payment.py", False),
            create_selectable_file("src/user.py", True),
        )
    )

    assert snapshot.total_count == 3
    assert snapshot.selected_count == 2
    assert snapshot.unselected_count == 1


def test_selected_paths_preserve_original_order() -> None:
    snapshot = FileSelectionSnapshot(
        files=(
            create_selectable_file("src/a.py", True),
            create_selectable_file("src/b.py", False),
            create_selectable_file("src/c.py", True),
        )
    )

    assert snapshot.selected_paths == (
        "src/a.py",
        "src/c.py",
    )


def test_snapshot_separates_selected_and_unselected_files() -> None:
    first = create_selectable_file("src/first.py", True)
    second = create_selectable_file("src/second.py", False)

    snapshot = FileSelectionSnapshot(files=(first, second))

    assert snapshot.selected_files == (first,)
    assert snapshot.unselected_files == (second,)


def test_snapshot_detects_existing_selection() -> None:
    snapshot = FileSelectionSnapshot(
        files=(
            create_selectable_file("src/auth.py", True),
            create_selectable_file("src/user.py", False),
        )
    )

    assert snapshot.has_selection is True


def test_snapshot_detects_when_all_files_are_selected() -> None:
    snapshot = FileSelectionSnapshot(
        files=(
            create_selectable_file("src/auth.py", True),
            create_selectable_file("src/user.py", True),
        )
    )

    assert snapshot.all_selected is True


def test_empty_snapshot_has_no_selection() -> None:
    snapshot = FileSelectionSnapshot(files=())

    assert snapshot.total_count == 0
    assert snapshot.selected_count == 0
    assert snapshot.unselected_count == 0
    assert snapshot.has_selection is False
    assert snapshot.all_selected is False


def test_snapshot_rejects_duplicate_file_paths() -> None:
    first = create_selectable_file("src/auth.py")
    second = create_selectable_file("src/auth.py", True)

    with pytest.raises(ValueError, match="Duplicate file paths"):
        FileSelectionSnapshot(files=(first, second))
