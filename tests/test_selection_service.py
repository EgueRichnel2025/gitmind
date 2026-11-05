"""Tests for the unified file selection service."""

import pytest

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot
from gitmind.core.selection.errors import FileNotFoundInSelectionError
from gitmind.core.selection.service import FileSelectionService


def make_snapshot(*paths: str) -> GitStatusSnapshot:
    """Create a Git status snapshot for testing."""
    files = tuple(
        GitFileStatus(
            path=path,
            index_status=" ",
            worktree_status="M",
        )
        for path in paths
    )
    return GitStatusSnapshot(files=files)


def make_service(page_size: int = 2) -> FileSelectionService:
    """Create a service with five files."""
    return FileSelectionService(
        make_snapshot(
            "src/auth.py",
            "src/main.py",
            "src/config.py",
            "tests/test_auth.py",
            "tests/test_main.py",
        ),
        page_size=page_size,
    )


def test_service_initializes_with_configured_page_size() -> None:
    service = make_service(page_size=3)

    assert service.page_size == 3
    assert service.current_page_number == 1


def test_service_returns_first_page() -> None:
    service = make_service()

    page = service.get_page()

    assert page.page_number == 1
    assert tuple(file.path for file in page.files) == (
        "src/auth.py",
        "src/main.py",
    )


def test_service_selects_file() -> None:
    service = make_service()

    page = service.select("src/auth.py")

    assert page.selected_on_page_count == 1
    assert page.total_selected == 1
    assert page.selected_paths == ("src/auth.py",)


def test_service_deselects_file() -> None:
    service = make_service()
    service.select("src/auth.py")

    page = service.deselect("src/auth.py")

    assert page.selected_on_page_count == 0
    assert page.total_selected == 0


def test_service_toggles_file_selection() -> None:
    service = make_service()

    selected_page = service.toggle("src/auth.py")
    deselected_page = service.toggle("src/auth.py")

    assert selected_page.selected_on_page_count == 1
    assert deselected_page.selected_on_page_count == 0


def test_service_selects_all_files_across_pages() -> None:
    service = make_service()

    page = service.select_all()

    assert page.total_items == 5
    assert page.total_selected == 5
    assert page.selected_on_page_count == 2

    selection = service.get_selection()

    assert selection.selected_count == 5
    assert selection.all_selected


def test_service_deselects_all_files_across_pages() -> None:
    service = make_service()
    service.select_all()

    page = service.deselect_all()

    assert page.total_selected == 0
    assert page.selected_on_page_count == 0
    assert service.get_selection().selected_count == 0


def test_service_navigates_to_next_page() -> None:
    service = make_service()

    page = service.next_page()

    assert page.page_number == 2
    assert tuple(file.path for file in page.files) == (
        "src/config.py",
        "tests/test_auth.py",
    )


def test_service_navigates_to_previous_page() -> None:
    service = make_service()

    service.next_page()
    page = service.previous_page()

    assert page.page_number == 1


def test_service_navigates_directly_to_page() -> None:
    service = make_service()

    page = service.go_to_page(3)

    assert page.page_number == 3
    assert page.files[0].path == "tests/test_main.py"


def test_selection_is_preserved_across_pages() -> None:
    service = make_service()

    service.select("src/auth.py")
    service.next_page()
    service.next_page()
    service.previous_page()
    service.previous_page()

    page = service.get_page()

    assert page.selected_paths == ("src/auth.py",)
    assert page.total_selected == 1


def test_selection_on_another_page_updates_global_count() -> None:
    service = make_service()

    service.go_to_page(2)
    service.select("src/config.py")

    service.go_to_page(1)
    page = service.get_page()

    assert page.total_selected == 1
    assert page.selected_on_page_count == 0


def test_get_selection_returns_all_selected_paths() -> None:
    service = make_service()

    service.select("src/auth.py")
    service.select("tests/test_main.py")

    selection = service.get_selection()

    assert selection.selected_paths == (
        "src/auth.py",
        "tests/test_main.py",
    )


def test_service_rejects_unknown_file() -> None:
    service = make_service()

    with pytest.raises(FileNotFoundInSelectionError):
        service.select("src/missing.py")


def test_service_rejects_invalid_snapshot() -> None:
    with pytest.raises(TypeError, match="GitStatusSnapshot"):
        FileSelectionService(None)  # type: ignore[arg-type]


def test_service_rejects_invalid_page_size() -> None:
    with pytest.raises(ValueError, match="greater than or equal"):
        FileSelectionService(make_snapshot("src/auth.py"), page_size=0)


def test_service_supports_empty_snapshot() -> None:
    service = FileSelectionService(make_snapshot())

    page = service.get_page()

    assert page.total_items == 0
    assert page.total_selected == 0
    assert page.item_count == 0


def test_service_keeps_current_page_after_selection() -> None:
    service = make_service()

    service.go_to_page(2)
    page = service.select("src/config.py")

    assert page.page_number == 2
    assert service.current_page_number == 2


def test_service_returns_updated_page_after_each_operation() -> None:
    service = make_service()

    service.select("src/auth.py")
    page = service.select("src/main.py")

    assert page.selected_paths == ("src/auth.py", "src/main.py")
    assert page.selected_on_page_count == 2
