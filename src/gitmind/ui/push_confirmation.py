"""Interactive confirmation interface for Git pushes."""

from collections.abc import Callable
from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from gitmind.core.git.commit_models import GitCommitResult


class PushConfirmationTerminalUI:
    """Ask the user to confirm pushing a successfully created commit."""

    def __init__(
        self,
        commit: GitCommitResult,
        branch: str,
        console: Console | None = None,
        confirm_prompt: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(commit, GitCommitResult):
            raise TypeError("commit must be a GitCommitResult instance.")

        if not isinstance(branch, str):
            raise TypeError("branch must be a string.")

        if not branch.strip():
            raise ValueError("branch cannot be empty.")

        self._commit = commit
        self._branch = branch
        self._console = console if console is not None else Console()
        self._confirm_prompt = confirm_prompt if confirm_prompt is not None else questionary.confirm

    def _display_header(self) -> None:
        """Display the commit and branch that are ready to be pushed."""
        content = Text()

        content.append("The following commit is ready to be pushed:\n\n", style="bold")

        content.append("Commit: ", style="bold")
        content.append(f"{self._commit.commit_hash[:12]}\n", style="cyan")

        content.append("Branch: ", style="bold")
        content.append(f"{self._branch}\n\n", style="white")

        content.append("Commit message:\n", style="bold")
        content.append(self._commit.message, style="green")

        content.append("\n\nPush this commit to the remote repository?", style="bold")

        self._console.print(
            Panel(
                content,
                title="GitMind | Push Confirmation",
                border_style="cyan",
                expand=False,
            )
        )

    def run(self) -> bool:
        """Return True only when the user explicitly confirms the push."""
        self._display_header()

        prompt = self._confirm_prompt(
            "Push this commit to the remote repository?",
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
