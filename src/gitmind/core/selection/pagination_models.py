"""Data models for file selection pagination."""

from dataclasses import dataclass

from gitmind.core.selection.models import SelectableFile


@dataclass(frozen=True, slots=True)
class FileSelectionPage:
    """Represent one immutable page of selectable files."""

    files: tuple[SelectableFile, ...]
    page_number: int
    page_size: int
    total_items: int
    total_pages: int
    total_selected: int

    def __post_init__(self) -> None:
        if not isinstance(self.files, tuple):
            raise TypeError("files must be a tuple.")

        if not all(isinstance(file, SelectableFile) for file in self.files):
            raise TypeError("files must contain only SelectableFile instances.")

        integer_fields = {
            "page_number": self.page_number,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "total_selected": self.total_selected,
        }

        for field_name, value in integer_fields.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer.")

        if self.page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1.")

        if self.page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1.")

        if self.total_items < 0:
            raise ValueError("total_items cannot be negative.")

        if self.total_selected < 0 or self.total_selected > self.total_items:
            raise ValueError("total_selected must be between 0 and total_items.")

        expected_total_pages = max(
            1,
            (self.total_items + self.page_size - 1) // self.page_size,
        )

        if self.total_pages != expected_total_pages:
            raise ValueError(
                f"total_pages must be {expected_total_pages} "
                f"for the given total_items and page_size."
            )

        if self.page_number > self.total_pages:
            raise ValueError("page_number cannot exceed total_pages.")

        expected_page_items = min(
            self.page_size,
            max(0, self.total_items - (self.page_number - 1) * self.page_size),
        )

        if len(self.files) != expected_page_items:
            raise ValueError(
                f"This page must contain {expected_page_items} files, "
                f"but received {len(self.files)}."
            )

        paths = [file.path for file in self.files]

        if len(paths) != len(set(paths)):
            raise ValueError("A page cannot contain duplicate file paths.")

        selected_on_page = sum(file.selected for file in self.files)

        if selected_on_page > self.total_selected:
            raise ValueError("Page selections cannot exceed total_selected.")

    @property
    def has_previous_page(self) -> bool:
        """Return whether a previous page exists."""
        return self.page_number > 1

    @property
    def has_next_page(self) -> bool:
        """Return whether a next page exists."""
        return self.page_number < self.total_pages

    @property
    def is_first_page(self) -> bool:
        """Return whether this is the first page."""
        return self.page_number == 1

    @property
    def is_last_page(self) -> bool:
        """Return whether this is the last page."""
        return self.page_number == self.total_pages

    @property
    def item_count(self) -> int:
        """Return the number of files displayed on this page."""
        return len(self.files)

    @property
    def selected_on_page_count(self) -> int:
        """Return the number of selected files on this page."""
        return sum(file.selected for file in self.files)

    @property
    def unselected_on_page_count(self) -> int:
        """Return the number of unselected files on this page."""
        return self.item_count - self.selected_on_page_count

    @property
    def total_unselected(self) -> int:
        """Return the number of unselected files across all pages."""
        return self.total_items - self.total_selected

    @property
    def selected_paths(self) -> tuple[str, ...]:
        """Return selected paths visible on this page."""
        return tuple(file.path for file in self.files if file.selected)
