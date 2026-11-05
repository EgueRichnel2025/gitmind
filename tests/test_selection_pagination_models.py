"""Tests for file selection pagination models."""

import pytest

from gitmind.core.git.status_models import GitFileStatus
from gitmind.core.selection.models import SelectableFile
from gitmind.core.selection.pagination_models import FileSelectionPage


def make_file(path: str, selected: bool = False) -> SelectableFile:
    """Create a selectable file for testing."""
    git_file = GitFileStatus(
        path=path,
        index_status=" ",
        worktree_status="M",
    )
    return SelectableFile(git_file=git_file, selected=selected)


def make_page(
    files: tuple[SelectableFile, ...],
    *,
    page_number: int = 1,
    page_size: int = 10,
    total_items: int = 10,
    total_pages: int = 1,
    total_selected: int = 0,
) -> FileSelectionPage:
    """Create a pagination model for testing."""
    return FileSelectionPage(
        files=files,
        page_number=page_number,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        total_selected=total_selected,
    )


def test_page_preserves_files_and_pagination_metadata() -> None:
    files = (make_file("src/auth.py"), make_file("src/main.py"))

    page = make_page(
        files,
        total_items=2,
    )

    assert page.files == files
    assert page.page_number == 1
    assert page.page_size == 10
    assert page.total_items == 2
    assert page.total_pages == 1


def test_first_page_has_no_previous_page() -> None:
    page = make_page(
        (make_file("src/auth.py"),),
        page_size=1,
        total_items=2,
        total_pages=2,
    )

    assert not page.has_previous_page
    assert page.has_next_page
    assert page.is_first_page
    assert not page.is_last_page


def test_last_page_has_no_next_page() -> None:
    page = make_page(
        (make_file("src/main.py"),),
        page_number=2,
        page_size=1,
        total_items=2,
        total_pages=2,
    )

    assert page.has_previous_page
    assert not page.has_next_page
    assert not page.is_first_page
    assert page.is_last_page


def test_page_calculates_file_counts() -> None:
    files = (
        make_file("src/auth.py", selected=True),
        make_file("src/main.py"),
        make_file("src/config.py", selected=True),
    )

    page = make_page(
        files,
        page_size=3,
        total_items=3,
        total_selected=2,
    )

    assert page.item_count == 3
    assert page.selected_on_page_count == 2
    assert page.unselected_on_page_count == 1
    assert page.total_unselected == 1


def test_page_returns_selected_paths() -> None:
    files = (
        make_file("src/auth.py", selected=True),
        make_file("src/main.py"),
        make_file("tests/test_auth.py", selected=True),
    )

    page = make_page(
        files,
        page_size=3,
        total_items=3,
        total_selected=2,
    )

    assert page.selected_paths == ("src/auth.py", "tests/test_auth.py")


def test_empty_page_is_supported() -> None:
    page = make_page(
        (),
        page_size=10,
        total_items=0,
        total_pages=1,
    )

    assert page.item_count == 0
    assert page.total_items == 0
    assert page.total_pages == 1
    assert not page.has_previous_page
    assert not page.has_next_page
    assert page.is_first_page
    assert page.is_last_page


def test_page_rejects_non_tuple_files() -> None:
    with pytest.raises(TypeError, match="tuple"):
        make_page([make_file("src/auth.py")])  # type: ignore[arg-type]


def test_page_rejects_invalid_file_objects() -> None:
    with pytest.raises(TypeError, match="SelectableFile"):
        make_page(("src/auth.py",))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("page_number", 0),
        ("page_size", 0),
        ("total_items", -1),
        ("total_selected", -1),
    ],
)
def test_page_rejects_invalid_numeric_values(field: str, value: int) -> None:
    files = (make_file("src/auth.py"),)

    parameters = {
        "page_number": 1,
        "page_size": 1,
        "total_items": 1,
        "total_pages": 1,
        "total_selected": 0,
    }
    parameters[field] = value

    with pytest.raises(ValueError):
        FileSelectionPage(files=files, **parameters)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("page_number", True),
        ("page_size", 10.5),
        ("total_items", "10"),
        ("total_pages", False),
        ("total_selected", 1.5),
    ],
)
def test_page_rejects_non_integer_metadata(field: str, value: object) -> None:
    parameters = {
        "files": (make_file("src/auth.py"),),
        "page_number": 1,
        "page_size": 1,
        "total_items": 1,
        "total_pages": 1,
        "total_selected": 0,
    }
    parameters[field] = value

    with pytest.raises(TypeError):
        FileSelectionPage(**parameters)  # type: ignore[arg-type]


def test_page_rejects_inconsistent_total_pages() -> None:
    with pytest.raises(ValueError, match="total_pages"):
        make_page(
            (make_file("src/auth.py"),),
            page_size=1,
            total_items=3,
            total_pages=2,
        )


def test_page_rejects_page_number_beyond_last_page() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        make_page(
            (make_file("src/auth.py"),),
            page_number=3,
            page_size=1,
            total_items=2,
            total_pages=2,
        )


def test_page_rejects_incorrect_number_of_files() -> None:
    with pytest.raises(ValueError, match="must contain"):
        make_page(
            (make_file("src/auth.py"),),
            page_size=2,
            total_items=2,
        )


def test_page_rejects_duplicate_paths() -> None:
    duplicate_files = (
        make_file("src/auth.py"),
        make_file("src/auth.py"),
    )

    with pytest.raises(ValueError, match="duplicate"):
        make_page(
            duplicate_files,
            page_size=2,
            total_items=2,
        )


def test_page_rejects_selected_count_greater_than_global_count() -> None:
    files = (
        make_file("src/auth.py", selected=True),
        make_file("src/main.py", selected=True),
    )

    with pytest.raises(ValueError, match="cannot exceed"):
        make_page(
            files,
            page_size=2,
            total_items=2,
            total_selected=1,
        )
