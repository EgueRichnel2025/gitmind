"""Interactive checkbox interface for GitMind file selection."""

from collections.abc import Callable
from typing import Any

import questionary
from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import (
    ConditionalContainer,
    FormattedTextControl,
    HSplit,
    Window,
)
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from gitmind.core.git.status_models import GitFileStatus
from gitmind.core.selection.models import FileSelectionSnapshot
from gitmind.core.selection.service import FileSelectionService

_QUIT_REQUESTED = object()


class SelectionTerminalUI:
    """Provide an intuitive multi-file selection interface."""

    def __init__(
        self,
        service: FileSelectionService,
        console: Console | None = None,
        checkbox_prompt: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(service, FileSelectionService):
            raise TypeError("service must be a FileSelectionService.")

        self._service = service
        self._console = console if console is not None else Console()
        self._checkbox_prompt = (
            checkbox_prompt if checkbox_prompt is not None else questionary.checkbox
        )
        self._quit_confirmed = False

    @property
    def quit_confirmed(self) -> bool:
        """Return whether the user explicitly confirmed quitting."""
        return self._quit_confirmed

    @staticmethod
    def _status_label(git_file: GitFileStatus) -> str:
        """Return a readable label for a Git file status."""
        if git_file.is_untracked:
            label = "UNTRACKED"
        elif git_file.is_unmerged:
            label = "CONFLICT"
        elif git_file.is_renamed:
            label = "RENAMED"
        elif git_file.is_copied:
            label = "COPIED"
        elif git_file.is_deleted:
            label = "DELETED"
        elif git_file.is_type_changed:
            label = "TYPE CHANGED"
        elif git_file.is_added:
            label = "ADDED"
        elif git_file.is_modified:
            label = "MODIFIED"
        else:
            label = git_file.status_code.strip() or "CHANGED"

        if git_file.is_staged and git_file.is_unstaged:
            label += " · STAGED + UNSTAGED"
        elif git_file.is_staged:
            label += " · STAGED"
        elif git_file.is_unstaged and not git_file.is_untracked:
            label += " · UNSTAGED"

        return label

    def _build_choices(self) -> list[questionary.Choice]:
        """Build checkbox choices from the current selection snapshot."""
        snapshot = self._service.get_selection()

        return [
            questionary.Choice(
                title=(f"{selectable_file.path}  [{self._status_label(selectable_file.git_file)}]"),
                value=selectable_file.path,
                checked=selectable_file.selected,
            )
            for selectable_file in snapshot.files
        ]

    def _display_header(self, total_files: int) -> None:
        """Display a short introduction before the interactive prompt."""
        message = Text.assemble(
            ("Choose the files GitMind should analyze.\n", "bold"),
            (f"{total_files} changed files detected.", "dim"),
        )

        self._console.print(
            Panel(
                message,
                title="GitMind | File Selection",
                border_style="cyan",
                expand=False,
            )
        )

    def _install_quit_confirmation(self, prompt: Any) -> None:
        """Add a reliable quit confirmation to the Questionary interface."""
        application = getattr(prompt, "application", None)

        if not isinstance(application, Application):
            return

        key_bindings = application.key_bindings

        if not isinstance(key_bindings, KeyBindings):
            return

        enter_binding = next(
            (binding for binding in key_bindings.bindings if binding.keys == (Keys.ControlM,)),
            None,
        )

        if enter_binding is None:
            raise RuntimeError("Questionary checkbox prompt has no Enter binding.")

        original_enter_handler = enter_binding.handler
        state = {"confirming_exit": False}

        confirmation_window = Window(
            content=FormattedTextControl(
                lambda: [
                    (
                        "class:question",
                        "Quit GitMind? Press Y to exit · N/Enter to continue.",
                    )
                ]
            ),
            height=1,
            dont_extend_height=True,
        )

        confirmation_container = ConditionalContainer(
            confirmation_window,
            filter=Condition(lambda: state["confirming_exit"]),
        )

        application.layout.container = HSplit(
            [
                application.layout.container,
                confirmation_container,
            ]
        )

        def request_exit(event: Any) -> None:
            """Display the quit confirmation."""
            state["confirming_exit"] = True
            event.app.invalidate()

        def continue_selection(event: Any) -> None:
            """Cancel quitting and return to file selection."""
            if state["confirming_exit"]:
                state["confirming_exit"] = False
                event.app.invalidate()

        def handle_confirmation(event: Any) -> None:
            """Only Y confirms quitting; every other character cancels."""
            if not state["confirming_exit"]:
                return

            if event.data.lower() == "y":
                self._quit_confirmed = True
                event.app.exit(result=_QUIT_REQUESTED)
                return

            continue_selection(event)

        def handle_enter(event: Any) -> None:
            """Use Enter to cancel confirmation or confirm file selection."""
            if state["confirming_exit"]:
                continue_selection(event)
                return

            original_enter_handler(event)

        # Q requests confirmation only when not already confirming.
        key_bindings.add(
            "q",
            filter=Condition(lambda: not state["confirming_exit"]),
            eager=True,
        )(request_exit)

        key_bindings.add(
            "Q",
            filter=Condition(lambda: not state["confirming_exit"]),
            eager=True,
        )(request_exit)

        # Catch all ordinary characters during confirmation.
        # Y exits; N and all other characters return to selection.
        key_bindings.add(
            Keys.Any,
            filter=Condition(lambda: state["confirming_exit"]),
            eager=True,
        )(handle_confirmation)

        # Replace Enter so it can dismiss the confirmation.
        key_bindings.remove(Keys.ControlM)
        key_bindings.add(Keys.ControlM, eager=True)(handle_enter)

        # Escape also dismisses the confirmation.
        key_bindings.add(Keys.Escape, eager=True)(continue_selection)

    def run(self) -> FileSelectionSnapshot | None:
        """Run the checkbox selection prompt.

        Return the confirmed selection, or None if the user cancels
        or explicitly confirms quitting.
        """
        self._quit_confirmed = False

        initial_snapshot = self._service.get_selection()

        if initial_snapshot.total_count == 0:
            return initial_snapshot

        self._display_header(initial_snapshot.total_count)

        choices = self._build_choices()

        prompt = self._checkbox_prompt(
            "Which files do you want to include?",
            choices=choices,
            instruction=(
                "(↑/↓ Navigate · Space Select · A Select all · "
                "I Invert · Q Quit · Enter Confirm · Ctrl+C Cancel)"
            ),
            use_arrow_keys=True,
            use_jk_keys=False,
            use_emacs_keys=False,
        )

        self._install_quit_confirmation(prompt)

        try:
            selected_paths = prompt.ask()
        except (KeyboardInterrupt, EOFError):
            return None

        if selected_paths is None:
            return None

        if selected_paths is _QUIT_REQUESTED:
            return None

        if not isinstance(selected_paths, list) or not all(
            isinstance(path, str) for path in selected_paths
        ):
            raise TypeError("The checkbox prompt must return a list of file paths.")

        known_paths = {file.path for file in initial_snapshot.files}
        unknown_paths = set(selected_paths) - known_paths

        if unknown_paths:
            raise ValueError(f"Unknown selected file paths: {sorted(unknown_paths)}")

        selected_path_set = set(selected_paths)

        self._service.deselect_all()

        # Preserve the original Git status order.
        for selectable_file in initial_snapshot.files:
            if selectable_file.path in selected_path_set:
                self._service.select(selectable_file.path)

        return self._service.get_selection()
