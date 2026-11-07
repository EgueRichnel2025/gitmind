"""Interactive interface for choosing a commit suggestion."""

from collections.abc import Callable
from typing import Any

import questionary
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from gitmind.core.ai.models import CommitSuggestionSet

_CANCEL_REQUESTED = object()


class CommitSuggestionTerminalUI:
    """Display three commit suggestions and return the chosen message."""

    def __init__(
        self,
        suggestions: CommitSuggestionSet,
        console: Console | None = None,
        select_prompt: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(suggestions, CommitSuggestionSet):
            raise TypeError("suggestions must be a CommitSuggestionSet instance.")

        self._suggestions = suggestions
        self._console = console if console is not None else Console()
        self._select_prompt = select_prompt if select_prompt is not None else questionary.select

    @staticmethod
    def _display_message(message: str) -> str:
        """Escape non-printable characters in untrusted generated text."""
        return "".join(
            character if character.isprintable() else f"\\u{ord(character):04x}"
            for character in message
        )

    def _build_choices(self) -> list[questionary.Choice]:
        """Build ordered choices from the generated suggestions."""
        return [
            questionary.Choice(
                title=(f"{index}. {self._display_message(suggestion.message)}"),
                value=index - 1,
            )
            for index, suggestion in enumerate(
                self._suggestions.suggestions,
                start=1,
            )
        ]

    def _display_header(self) -> None:
        """Display the commit suggestion selection header."""
        message = Text.assemble(
            ("Choose the commit message that best\n", "bold"),
            ("describes your changes.", "dim"),
        )

        self._console.print(
            Panel(
                message,
                title="GitMind | Commit Suggestions",
                border_style="cyan",
                expand=False,
            )
        )

    def _install_cancel_binding(self, prompt: Any) -> None:
        """Allow Q to cancel the suggestion selection."""
        application = getattr(prompt, "application", None)

        if not isinstance(application, Application):
            return

        key_bindings = application.key_bindings

        if not isinstance(key_bindings, KeyBindings):
            return

        def cancel(event: Any) -> None:
            """Exit the prompt without selecting a suggestion."""
            event.app.exit(result=_CANCEL_REQUESTED)

        key_bindings.add(
            "q",
            eager=True,
        )(cancel)

        key_bindings.add(
            "Q",
            eager=True,
        )(cancel)

    def run(self) -> str | None:
        """Run the interactive prompt and return the selected message.

        Return None when the user cancels the selection.
        """
        self._display_header()

        prompt = self._select_prompt(
            "Which commit message do you prefer?",
            choices=self._build_choices(),
            instruction="(↑/↓ Navigate · Enter Confirm · Q Cancel · Ctrl+C Cancel)",
            use_shortcuts=False,
            use_arrow_keys=True,
            use_jk_keys=False,
            use_emacs_keys=False,
        )

        self._install_cancel_binding(prompt)

        try:
            selected_index = prompt.ask()
        except (KeyboardInterrupt, EOFError):
            return None

        if selected_index is None or selected_index is _CANCEL_REQUESTED:
            return None

        if (
            isinstance(selected_index, bool)
            or not isinstance(selected_index, int)
            or not 0 <= selected_index < len(self._suggestions.suggestions)
        ):
            raise TypeError("The selection prompt must return a valid suggestion index.")

        return self._suggestions.suggestions[selected_index].message
