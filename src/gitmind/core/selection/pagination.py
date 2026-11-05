"""Pagination engine for GitMind file selection."""

from gitmind.core.selection.models import FileSelectionSnapshot
from gitmind.core.selection.pagination_models import FileSelectionPage
from gitmind.core.selection.selector import FileSelector


class FileSelectionPager:
    """Navigate through selectable files without modifying their selection."""

    def __init__(self, selector: FileSelector, page_size: int = 10) -> None:
        if not isinstance(selector, FileSelector):
            raise TypeError("selector must be a FileSelector.")

        self._validate_page_size(page_size)

        self._selector = selector
        self._page_size = page_size
        self._current_page_number = 1

    @staticmethod
    def _validate_page_size(page_size: int) -> None:
        """Validate the configured number of files per page."""
        if isinstance(page_size, bool) or not isinstance(page_size, int):
            raise TypeError("page_size must be an integer.")

        if page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1.")

    @property
    def page_size(self) -> int:
        """Return the configured number of files per page."""
        return self._page_size

    @property
    def current_page_number(self) -> int:
        """Return the current page number."""
        return self._current_page_number

    @staticmethod
    def _calculate_total_pages(total_items: int, page_size: int) -> int:
        """Calculate the number of pages, keeping one page for empty results."""
        return max(1, (total_items + page_size - 1) // page_size)

    def _get_snapshot(self) -> FileSelectionSnapshot:
        """Retrieve the latest selection state."""
        return self._selector.get_selection()

    def get_page(self) -> FileSelectionPage:
        """Return the current page using the latest selection state."""
        snapshot = self._get_snapshot()

        total_items = snapshot.total_count
        total_selected = snapshot.selected_count
        total_pages = self._calculate_total_pages(total_items, self._page_size)

        if self._current_page_number > total_pages:
            self._current_page_number = total_pages

        start_index = (self._current_page_number - 1) * self._page_size
        end_index = start_index + self._page_size

        page_files = snapshot.files[start_index:end_index]

        return FileSelectionPage(
            files=page_files,
            page_number=self._current_page_number,
            page_size=self._page_size,
            total_items=total_items,
            total_pages=total_pages,
            total_selected=total_selected,
        )

    def next_page(self) -> FileSelectionPage:
        """Navigate to the next page when one exists."""
        snapshot = self._get_snapshot()

        total_pages = self._calculate_total_pages(
            snapshot.total_count,
            self._page_size,
        )

        if self._current_page_number < total_pages:
            self._current_page_number += 1

        return self.get_page()

    def previous_page(self) -> FileSelectionPage:
        """Navigate to the previous page when one exists."""
        if self._current_page_number > 1:
            self._current_page_number -= 1

        return self.get_page()

    def go_to_page(self, page_number: int) -> FileSelectionPage:
        """Navigate directly to a specific page."""
        if isinstance(page_number, bool) or not isinstance(page_number, int):
            raise TypeError("page_number must be an integer.")

        snapshot = self._get_snapshot()

        total_pages = self._calculate_total_pages(
            snapshot.total_count,
            self._page_size,
        )

        if not 1 <= page_number <= total_pages:
            raise ValueError(
                f"page_number must be between 1 and {total_pages}."
            )

        self._current_page_number = page_number

        return self.get_page()
