"""Interactive confirmation interface for Git staging."""

from collections.abc import Callable
from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from gitmind.core.selection.models import FileSelectionSnapshot


class StagingConfirmationTerminalUI:
    """Ask the user to confirm staging the selected files."""

    def __init__(
        self,
        selection: FileSelectionSnapshot,
        console: Console | None = None,
        confirm_prompt: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(selection, FileSelectionSnapshot):
            raise TypeError("selection must be a FileSelectionSnapshot instance.")

        if not selection.has_selection:
            raise ValueError("Cannot confirm staging without selected files.")

        self._selection = selection
        self._console = console if console is not None else Console()
        self._confirm_prompt = confirm_prompt if confirm_prompt is not None else questionary.confirm

    def _display_header(self) -> None:
        """Display the staging confirmation panel."""
        content = Text()
        content.append(
            "The following files will be staged:\n\n",
            style="bold",
        )

        for path in self._selection.selected_paths:
            content.append("  ✓ ", style="green")
            content.append(path, style="white")
            content.append("\n")

        content.append(
            "\nDo you want to stage these files?",
            style="bold",
        )

        self._console.print(
            Panel(
                content,
                title="GitMind | Staging Confirmation",
                border_style="cyan",
                expand=False,
            )
        )

    def run(self) -> bool:
        """Ask for explicit staging confirmation.

        Return True only when the user explicitly confirms.
        Cancellation and invalid prompt termination are treated as refusal.
        """
        self._display_header()

        prompt = self._confirm_prompt(
            "Stage selected files?",
            default=False,
        )

        try:
            confirmed = prompt.ask()
        except (KeyboardInterrupt, EOFError):
            return False

        if confirmed is None:
            return False

        if not isinstance(confirmed, bool):
            raise TypeError("The confirmation prompt must return a boolean or None.")

        return confirmed
