"""Interactive confirmation interface for Git commits."""

from collections.abc import Callable
from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from gitmind.core.selection.models import FileSelectionSnapshot


class CommitConfirmationTerminalUI:
    """Ask the user to confirm a commit with a selected message."""

    def __init__(
        self,
        selection: FileSelectionSnapshot,
        message: str,
        console: Console | None = None,
        confirm_prompt: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(selection, FileSelectionSnapshot):
            raise TypeError("selection must be a FileSelectionSnapshot instance.")

        if not selection.has_selection:
            raise ValueError("Cannot confirm a commit without selected files.")

        if not isinstance(message, str):
            raise TypeError("message must be a string.")

        if not message.strip():
            raise ValueError("Commit message cannot be empty.")

        self._selection = selection
        self._message = message
        self._console = console if console is not None else Console()
        self._confirm_prompt = confirm_prompt if confirm_prompt is not None else questionary.confirm

    def _display_header(self) -> None:
        """Display the selected files and proposed commit message."""
        content = Text()

        content.append(
            "The following files will be included in the commit:\n\n",
            style="bold",
        )

        for path in self._selection.selected_paths:
            content.append("  ✓ ", style="green")
            content.append(path, style="white")
            content.append("\n")

        content.append("\nCommit message:\n", style="bold")
        content.append(self._message, style="green")
        content.append("\n\nCreate this commit?", style="bold")

        self._console.print(
            Panel(
                content,
                title="GitMind | Commit Confirmation",
                border_style="cyan",
                expand=False,
            )
        )

    def run(self) -> bool:
        """Ask for explicit commit confirmation.

        Return True only when the user explicitly confirms.
        Cancellation and invalid prompt termination are treated as refusal.
        """
        self._display_header()

        prompt = self._confirm_prompt(
            "Create this commit?",
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
