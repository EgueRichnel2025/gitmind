"""Tests for the public file selection API."""

import gitmind.core.selection as selection
from gitmind.core.git.status_models import GitStatusSnapshot
from gitmind.core.selection.errors import (
    FileNotFoundInSelectionError,
    FileSelectionError,
)
from gitmind.core.selection.models import FileSelectionSnapshot, SelectableFile
from gitmind.core.selection.pagination import FileSelectionPager
from gitmind.core.selection.pagination_models import FileSelectionPage
from gitmind.core.selection.selector import FileSelector
from gitmind.core.selection.service import FileSelectionService


def test_public_api_exposes_all_documented_symbols() -> None:
    expected_symbols = {
        "FileNotFoundInSelectionError",
        "FileSelectionError",
        "FileSelectionPage",
        "FileSelectionPager",
        "FileSelectionService",
        "FileSelectionSnapshot",
        "FileSelector",
        "SelectableFile",
    }

    assert set(selection.__all__) == expected_symbols


def test_public_api_exports_original_classes() -> None:
    assert selection.FileNotFoundInSelectionError is FileNotFoundInSelectionError
    assert selection.FileSelectionError is FileSelectionError
    assert selection.FileSelectionPage is FileSelectionPage
    assert selection.FileSelectionPager is FileSelectionPager
    assert selection.FileSelectionService is FileSelectionService
    assert selection.FileSelectionSnapshot is FileSelectionSnapshot
    assert selection.FileSelector is FileSelector
    assert selection.SelectableFile is SelectableFile


def test_public_api_can_create_and_use_selection_service() -> None:
    snapshot = GitStatusSnapshot(files=())

    service = selection.FileSelectionService(snapshot)
    page = service.get_page()
    selected_files = service.get_selection()

    assert isinstance(service, selection.FileSelectionService)
    assert isinstance(page, selection.FileSelectionPage)
    assert isinstance(selected_files, selection.FileSelectionSnapshot)
    assert page.total_items == 0
    assert selected_files.selected_count == 0
