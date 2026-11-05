"""Terminal interface for interactive file selection."""

from collections.abc import Callable

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gitmind.core.selection.models import FileSelectionSnapshot
from gitmind.core.selection.pagination_models import FileSelectionPage
from gitmind.core.selection.service import FileSelectionService


class SelectionTerminalUI:
    """Provide an interactive terminal interface for file selection."""

    def __init__(
        self,
        service: FileSelectionService,
        console: Console | None = None,
        input_provider: Callable[[str], str] | None = None,
    ) -> None:
        if not isinstance(service, FileSelectionService):
            raise TypeError("service must be a FileSelectionService.")

        self._service = service
        self._console = console if console is not None else Console()
        self._input_provider = input_provider if input_provider is not None else input

    def _render_page(self, page: FileSelectionPage) -> None:
        """Display the current page and available interactions."""
        self._console.print()

        self._console.print(
            Panel(
                Text("Select the files you want to include in the next analysis."),
                title="GitMind | File Selection",
                expand=False,
            )
        )

        table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold",
            expand=True,
        )

        table.add_column("#", justify="right", width=4)
        table.add_column("Selected", justify="center", width=10)
        table.add_column("File", overflow="fold")
        table.add_column("Git status", justify="center", width=10)

        for index, selectable_file in enumerate(page.files, start=1):
            git_file = selectable_file.git_file

            marker = "[x]" if selectable_file.selected else "[ ]"
            status = git_file.status_code.strip() or "--"

            table.add_row(
                str(index),
                Text(marker),
                Text(selectable_file.path),
                status,
            )

        self._console.print(table)

        self._console.print(
            Text(
                f"Page: {page.page_number}/{page.total_pages} | "
                f"Files: {page.total_items} | "
                f"Selected: {page.total_selected}"
            )
        )

        self._console.print(
            Text(
                "Commands: N = next | P = previous | A = select all | "
                "D = deselect all | 1-10 = toggle file | Enter = confirm | "
                "Q = cancel"
            )
        )

    def _toggle_file(self, page: FileSelectionPage, index: int) -> None:
        """Toggle the selection state of a file on the current page."""
        if not 1 <= index <= page.item_count:
            self._console.print(
                Text(f"Invalid file number. Choose a number between 1 and {page.item_count}.")
            )
            return

        selected_file = page.files[index - 1]
        self._service.toggle(selected_file.path)

    def run(self) -> FileSelectionSnapshot | None:
        """Run the interactive selection loop.

        Return the final snapshot on confirmation, or None on cancellation.
        """
        while True:
            page = self._service.get_page()
            self._render_page(page)

            try:
                action = self._input_provider("Action: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                self._console.print(Text("Selection cancelled."))
                return None

            if action == "":
                return self._service.get_selection()

            if action in {"q", "quit"}:
                self._console.print(Text("Selection cancelled."))
                return None

            if action in {"n", "next"}:
                if page.has_next_page:
                    self._service.next_page()
                else:
                    self._console.print(Text("You are already on the last page."))
                continue

            if action in {"p", "previous"}:
                if page.has_previous_page:
                    self._service.previous_page()
                else:
                    self._console.print(Text("You are already on the first page."))
                continue

            if action == "a":
                self._service.select_all()
                self._console.print(Text("All files selected."))
                continue

            if action == "d":
                self._service.deselect_all()
                self._console.print(Text("All files deselected."))
                continue

            if action.isdecimal():
                self._toggle_file(page, int(action))
                continue

            self._console.print(
                Text("Unknown command. Enter a file number, N, P, A, D, Enter or Q.")
            )
