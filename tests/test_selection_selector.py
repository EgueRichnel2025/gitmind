"""Tests for file selection operations."""

import pytest

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot
from gitmind.core.selection.errors import FileNotFoundInSelectionError
from gitmind.core.selection.selector import FileSelector


def make_git_file(path: str) -> GitFileStatus:
    """Create a Git file status for testing."""
    return GitFileStatus(
        path=path,
        index_status=" ",
        worktree_status="M",
    )


def make_snapshot(*paths: str) -> GitStatusSnapshot:
    """Create a Git status snapshot for testing."""
    files = tuple(make_git_file(path) for path in paths)
    return GitStatusSnapshot(files=files)


def test_selector_starts_with_all_files_unselected() -> None:
    selector = FileSelector(make_snapshot("src/auth.py", "src/main.py"))

    selection = selector.get_selection()

    assert selection.total_count == 2
    assert selection.selected_count == 0
    assert selection.unselected_count == 2
    assert not selection.has_selection


def test_selector_preserves_file_order() -> None:
    selector = FileSelector(make_snapshot("src/auth.py", "src/main.py", "tests/test_auth.py"))

    selector.select("tests/test_auth.py")
    selector.select("src/auth.py")

    selection = selector.get_selection()

    assert tuple(file.path for file in selection.files) == (
        "src/auth.py",
        "src/main.py",
        "tests/test_auth.py",
    )
    assert selection.selected_paths == ("src/auth.py", "tests/test_auth.py")


def test_selector_preserves_git_file_metadata() -> None:
    git_file = make_git_file("src/auth.py")
    snapshot = GitStatusSnapshot(files=(git_file,))

    selector = FileSelector(snapshot)

    selected_file = selector.get_selection().files[0]

    assert selected_file.git_file is git_file


def test_select_marks_file_and_returns_updated_snapshot() -> None:
    selector = FileSelector(make_snapshot("src/auth.py", "src/main.py"))

    selection = selector.select("src/auth.py")

    assert selection.selected_count == 1
    assert selection.selected_paths == ("src/auth.py",)


def test_select_is_idempotent() -> None:
    selector = FileSelector(make_snapshot("src/auth.py"))

    selector.select("src/auth.py")
    selection = selector.select("src/auth.py")

    assert selection.selected_count == 1
    assert selection.all_selected


def test_deselect_unselects_file() -> None:
    selector = FileSelector(make_snapshot("src/auth.py"))
    selector.select("src/auth.py")

    selection = selector.deselect("src/auth.py")

    assert selection.selected_count == 0
    assert not selection.has_selection


def test_toggle_switches_selection_state() -> None:
    selector = FileSelector(make_snapshot("src/auth.py"))

    first_selection = selector.toggle("src/auth.py")
    second_selection = selector.toggle("src/auth.py")

    assert first_selection.selected_count == 1
    assert second_selection.selected_count == 0


def test_select_all_selects_every_file() -> None:
    selector = FileSelector(make_snapshot("src/auth.py", "src/main.py", "tests/test_auth.py"))

    selection = selector.select_all()

    assert selection.total_count == 3
    assert selection.selected_count == 3
    assert selection.all_selected


def test_deselect_all_clears_every_selection() -> None:
    selector = FileSelector(make_snapshot("src/auth.py", "src/main.py"))
    selector.select_all()

    selection = selector.deselect_all()

    assert selection.selected_count == 0
    assert selection.unselected_count == 2
    assert not selection.has_selection


def test_empty_snapshot_is_supported() -> None:
    selector = FileSelector(make_snapshot())

    selection = selector.select_all()

    assert selection.total_count == 0
    assert selection.selected_count == 0
    assert not selection.all_selected


@pytest.mark.parametrize("operation", ["select", "deselect", "toggle"])
def test_unknown_file_raises_selection_error(operation: str) -> None:
    selector = FileSelector(make_snapshot("src/auth.py"))

    with pytest.raises(FileNotFoundInSelectionError) as exc_info:
        getattr(selector, operation)("src/missing.py")

    assert exc_info.value.path == "src/missing.py"


def test_selector_rejects_invalid_snapshot() -> None:
    with pytest.raises(TypeError, match="GitStatusSnapshot"):
        FileSelector(None)  # type: ignore[arg-type]


def test_selector_rejects_non_string_path() -> None:
    selector = FileSelector(make_snapshot("src/auth.py"))

    with pytest.raises(TypeError, match="string"):
        selector.select(None)  # type: ignore[arg-type]


def test_selector_rejects_empty_path() -> None:
    selector = FileSelector(make_snapshot("src/auth.py"))

    with pytest.raises(ValueError, match="empty"):
        selector.select("")


def test_previous_snapshot_is_not_modified() -> None:
    selector = FileSelector(make_snapshot("src/auth.py"))

    initial_snapshot = selector.get_selection()
    selector.select("src/auth.py")

    assert initial_snapshot.selected_count == 0
    assert selector.get_selection().selected_count == 1
