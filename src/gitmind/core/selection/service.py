"""Unified application service for file selection and pagination."""

from gitmind.core.git.status_models import GitStatusSnapshot
from gitmind.core.selection.models import FileSelectionSnapshot
from gitmind.core.selection.pagination import FileSelectionPager
from gitmind.core.selection.pagination_models import FileSelectionPage
from gitmind.core.selection.selector import FileSelector


class FileSelectionService:
    """Coordinate file selection and pagination through one public API."""

    def __init__(
        self,
        snapshot: GitStatusSnapshot,
        page_size: int = 10,
    ) -> None:
        if not isinstance(snapshot, GitStatusSnapshot):
            raise TypeError("snapshot must be a GitStatusSnapshot.")

        self._selector = FileSelector(snapshot)
        self._pager = FileSelectionPager(self._selector, page_size=page_size)

    @property
    def page_size(self) -> int:
        """Return the configured page size."""
        return self._pager.page_size

    @property
    def current_page_number(self) -> int:
        """Return the current page number."""
        return self._pager.current_page_number

    def get_page(self) -> FileSelectionPage:
        """Return the current page with the latest selection state."""
        return self._pager.get_page()

    def next_page(self) -> FileSelectionPage:
        """Navigate to the next page."""
        return self._pager.next_page()

    def previous_page(self) -> FileSelectionPage:
        """Navigate to the previous page."""
        return self._pager.previous_page()

    def go_to_page(self, page_number: int) -> FileSelectionPage:
        """Navigate directly to a specific page."""
        return self._pager.go_to_page(page_number)

    def select(self, path: str) -> FileSelectionPage:
        """Select a file and return the updated current page."""
        self._selector.select(path)
        return self.get_page()

    def deselect(self, path: str) -> FileSelectionPage:
        """Deselect a file and return the updated current page."""
        self._selector.deselect(path)
        return self.get_page()

    def toggle(self, path: str) -> FileSelectionPage:
        """Invert a file's selection state."""
        self._selector.toggle(path)
        return self.get_page()

    def select_all(self) -> FileSelectionPage:
        """Select every available file."""
        self._selector.select_all()
        return self.get_page()

    def deselect_all(self) -> FileSelectionPage:
        """Deselect every available file."""
        self._selector.deselect_all()
        return self.get_page()

    def get_selection(self) -> FileSelectionSnapshot:
        """Return the complete selection across all pages."""
        return self._selector.get_selection()
