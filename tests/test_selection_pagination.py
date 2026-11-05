"""Tests for the file selection pagination engine."""

import pytest

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot
from gitmind.core.selection.pagination import FileSelectionPager
from gitmind.core.selection.selector import FileSelector


def make_selector(*paths: str) -> FileSelector:
    """Create a file selector containing the provided paths."""
    files = tuple(
        GitFileStatus(
            path=path,
            index_status=" ",
            worktree_status="M",
        )
        for path in paths
    )

    return FileSelector(GitStatusSnapshot(files=files))


def make_pager(page_size: int = 2) -> FileSelectionPager:
    """Create a pager with five selectable files."""
    selector = make_selector(
        "src/auth.py",
        "src/main.py",
        "src/config.py",
        "tests/test_auth.py",
        "tests/test_main.py",
    )

    return FileSelectionPager(selector, page_size=page_size)


def test_pager_initializes_on_first_page() -> None:
    pager = make_pager()

    page = pager.get_page()

    assert pager.current_page_number == 1
    assert pager.page_size == 2
    assert page.page_number == 1


def test_pager_returns_first_page_files() -> None:
    pager = make_pager()

    page = pager.get_page()

    assert tuple(file.path for file in page.files) == (
        "src/auth.py",
        "src/main.py",
    )


def test_pager_calculates_total_pages() -> None:
    pager = make_pager(page_size=2)

    page = pager.get_page()

    assert page.total_items == 5
    assert page.total_pages == 3


def test_next_page_returns_following_files() -> None:
    pager = make_pager()

    page = pager.next_page()

    assert page.page_number == 2
    assert tuple(file.path for file in page.files) == (
        "src/config.py",
        "tests/test_auth.py",
    )


def test_previous_page_returns_preceding_files() -> None:
    pager = make_pager()

    pager.next_page()
    page = pager.previous_page()

    assert page.page_number == 1
    assert tuple(file.path for file in page.files) == (
        "src/auth.py",
        "src/main.py",
    )


def test_last_page_contains_remaining_files() -> None:
    pager = make_pager()

    pager.go_to_page(3)
    page = pager.get_page()

    assert page.page_number == 3
    assert page.item_count == 1
    assert page.files[0].path == "tests/test_main.py"
    assert page.is_last_page


def test_next_page_does_not_exceed_last_page() -> None:
    pager = make_pager()

    pager.go_to_page(3)
    page = pager.next_page()

    assert page.page_number == 3
    assert page.is_last_page


def test_previous_page_does_not_go_before_first_page() -> None:
    pager = make_pager()

    page = pager.previous_page()

    assert page.page_number == 1
    assert page.is_first_page


def test_go_to_page_navigates_directly() -> None:
    pager = make_pager()

    page = pager.go_to_page(3)

    assert page.page_number == 3
    assert page.files[0].path == "tests/test_main.py"


@pytest.mark.parametrize("page_number", [0, -1, 4])
def test_go_to_page_rejects_out_of_range_numbers(page_number: int) -> None:
    pager = make_pager()

    with pytest.raises(ValueError, match="between"):
        pager.go_to_page(page_number)


@pytest.mark.parametrize("page_number", ["2", 2.5, True])
def test_go_to_page_rejects_non_integer_values(page_number: object) -> None:
    pager = make_pager()

    with pytest.raises(TypeError, match="integer"):
        pager.go_to_page(page_number)  # type: ignore[arg-type]


def test_pager_rejects_invalid_selector() -> None:
    with pytest.raises(TypeError, match="FileSelector"):
        FileSelectionPager(None)  # type: ignore[arg-type]


@pytest.mark.parametrize("page_size", ["10", 2.5, True])
def test_pager_rejects_non_integer_page_size(page_size: object) -> None:
    selector = make_selector("src/auth.py")

    with pytest.raises(TypeError, match="integer"):
        FileSelectionPager(selector, page_size=page_size)  # type: ignore[arg-type]


@pytest.mark.parametrize("page_size", [0, -1])
def test_pager_rejects_invalid_page_size(page_size: int) -> None:
    selector = make_selector("src/auth.py")

    with pytest.raises(ValueError, match="greater than or equal"):
        FileSelectionPager(selector, page_size=page_size)


def test_pager_supports_empty_selection() -> None:
    selector = make_selector()
    pager = FileSelectionPager(selector)

    page = pager.get_page()

    assert page.total_items == 0
    assert page.total_pages == 1
    assert page.item_count == 0
    assert not page.has_next_page
    assert not page.has_previous_page


def test_pager_supports_single_page() -> None:
    selector = make_selector("src/auth.py", "src/main.py")
    pager = FileSelectionPager(selector, page_size=10)

    page = pager.get_page()

    assert page.total_pages == 1
    assert page.is_first_page
    assert page.is_last_page


def test_selection_is_preserved_when_navigating_between_pages() -> None:
    selector = make_selector(
        "src/auth.py",
        "src/main.py",
        "src/config.py",
        "tests/test_auth.py",
    )

    pager = FileSelectionPager(selector, page_size=2)

    selector.select("src/auth.py")
    pager.next_page()

    page = pager.get_page()

    assert page.page_number == 2
    assert page.total_selected == 1

    pager.previous_page()
    page = pager.get_page()

    assert page.selected_paths == ("src/auth.py",)
    assert page.total_selected == 1


def test_pager_reads_selection_changes_made_after_initialization() -> None:
    selector = make_selector("src/auth.py", "src/main.py")
    pager = FileSelectionPager(selector)

    selector.select("src/main.py")

    page = pager.get_page()

    assert page.total_selected == 1
    assert page.selected_paths == ("src/main.py",)


def test_navigation_does_not_change_selection_state() -> None:
    selector = make_selector(
        "src/auth.py",
        "src/main.py",
        "src/config.py",
        "tests/test_auth.py",
    )

    selector.select("src/auth.py")
    pager = FileSelectionPager(selector, page_size=2)

    pager.next_page()
    pager.previous_page()

    assert selector.get_selection().selected_paths == ("src/auth.py",)


def test_global_selection_count_is_available_on_every_page() -> None:
    selector = make_selector(
        "src/auth.py",
        "src/main.py",
        "src/config.py",
        "tests/test_auth.py",
    )

    selector.select("src/auth.py")
    selector.select("src/config.py")

    pager = FileSelectionPager(selector, page_size=2)

    first_page = pager.get_page()
    second_page = pager.next_page()

    assert first_page.total_selected == 2
    assert second_page.total_selected == 2

    assert first_page.selected_on_page_count == 1
    assert second_page.selected_on_page_count == 1
