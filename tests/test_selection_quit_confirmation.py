"""Tests for explicit quit confirmation in the terminal selection UI."""

from types import SimpleNamespace
from unittest.mock import Mock

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import FormattedTextControl, Layout, Window
from prompt_toolkit.output import DummyOutput

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot
from gitmind.core.selection.service import FileSelectionService
from gitmind.ui.selection import _QUIT_REQUESTED, SelectionTerminalUI


class FakeRuntimeApplication:
    """Simulate the running Prompt Toolkit application."""

    def __init__(self) -> None:
        self.invalidations = 0
        self.exit_result = None

    def invalidate(self) -> None:
        self.invalidations += 1

    def exit(self, result=None) -> None:
        self.exit_result = result


def make_ui() -> SelectionTerminalUI:
    """Create a terminal UI for testing quit confirmation."""
    service = FileSelectionService(
        GitStatusSnapshot(files=(GitFileStatus("src/main.py", " ", "M"),))
    )

    return SelectionTerminalUI(
        service=service,
        checkbox_prompt=Mock(),
    )


def make_prompt():
    """Create a Prompt Toolkit application without starting it."""
    key_bindings = KeyBindings()
    enter_calls = []

    @key_bindings.add(Keys.ControlM, eager=True)
    def original_enter(_event):
        enter_calls.append("submitted")

    application = Application(
        layout=Layout(Window(FormattedTextControl("File selection"))),
        key_bindings=key_bindings,
        output=DummyOutput(),
    )

    prompt = SimpleNamespace(application=application)

    return prompt, key_bindings, enter_calls


def get_handler(key_bindings: KeyBindings, key):
    """Return the handler registered for a specific key."""
    matches = [binding.handler for binding in key_bindings.bindings if binding.keys == (key,)]

    assert len(matches) == 1

    return matches[0]


def test_q_requires_confirmation_and_n_keeps_selection_open() -> None:
    ui = make_ui()
    prompt, bindings, _ = make_prompt()

    ui._install_quit_confirmation(prompt)

    runtime = FakeRuntimeApplication()
    event = SimpleNamespace(app=runtime)

    request_exit = get_handler(bindings, "q")
    handle_confirmation = get_handler(bindings, Keys.Any)

    request_exit(event)

    assert runtime.invalidations == 1
    assert runtime.exit_result is None
    assert ui.quit_confirmed is False

    # N cancels the quit request.
    handle_confirmation(SimpleNamespace(app=runtime, data="n"))

    assert runtime.invalidations == 2
    assert runtime.exit_result is None
    assert ui.quit_confirmed is False

    # Y without an active confirmation must do nothing.
    handle_confirmation(SimpleNamespace(app=runtime, data="y"))

    assert runtime.exit_result is None

    # A new Q followed by Y confirms quitting.
    request_exit(event)
    handle_confirmation(SimpleNamespace(app=runtime, data="y"))

    assert runtime.exit_result is _QUIT_REQUESTED
    assert ui.quit_confirmed is True


def test_enter_dismisses_quit_confirmation_before_submitting() -> None:
    ui = make_ui()
    prompt, bindings, enter_calls = make_prompt()

    ui._install_quit_confirmation(prompt)

    runtime = FakeRuntimeApplication()
    event = SimpleNamespace(app=runtime)

    request_exit = get_handler(bindings, "q")
    handle_enter = get_handler(bindings, Keys.ControlM)

    request_exit(event)
    handle_enter(event)

    assert enter_calls == []
    assert runtime.exit_result is None
    assert ui.quit_confirmed is False

    # Enter works normally after dismissing the confirmation.
    handle_enter(event)

    assert runtime.exit_result is None
    assert enter_calls == ["submitted"]
