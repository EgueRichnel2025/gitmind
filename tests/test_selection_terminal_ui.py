"""Tests for the interactive file selection terminal interface."""

from io import StringIO

import pytest
from rich.console import Console

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot
from gitmind.core.selection.models import FileSelectionSnapshot
from gitmind.core.selection.service import FileSelectionService
from gitmind.ui.selection import SelectionTerminalUI


def make_service(page_size: int = 2) -> FileSelectionService:
    """Create a selection service containing five files."""
    files = tuple(
        GitFileStatus(
            path=path,
            index_status=" ",
            worktree_status="M",
        )
        for path in (
            "src/auth.py",
            "src/main.py",
            "src/config.py",
            "tests/test_auth.py",
            "tests/test_main.py",
        )
    )

    return FileSelectionService(
        GitStatusSnapshot(files=files),
        page_size=page_size,
    )


def make_ui(
    service: FileSelectionService,
    actions: list[str],
    output: StringIO | None = None,
) -> tuple[SelectionTerminalUI, StringIO]:
    """Create a terminal UI with simulated user input."""
    output = output if output is not None else StringIO()
    console = Console(
        file=output,
        force_terminal=False,
        color_system=None,
        width=120,
    )

    action_iterator = iter(actions)

    def provide_input(_prompt: str) -> str:
        return next(action_iterator)

    return SelectionTerminalUI(
        service=service,
        console=console,
        input_provider=provide_input,
    ), output


def test_ui_renders_files_and_confirms_selection() -> None:
    service = make_service()
    ui, output = make_ui(service, ["1", ""])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_paths == ("src/auth.py",)

    rendered = output.getvalue()

    assert "GitMind" in rendered
    assert "src/auth.py" in rendered
    assert "src/main.py" in rendered
    assert "Selected: 0" in rendered


def test_ui_preserves_selection_across_pages() -> None:
    service = make_service()
    ui, _ = make_ui(service, ["1", "n", "1", "p", ""])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_paths == ("src/auth.py", "src/config.py")


def test_ui_select_all_affects_every_page() -> None:
    service = make_service()
    ui, _ = make_ui(service, ["a", ""])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_count == 5
    assert result.all_selected


def test_ui_deselect_all_affects_every_page() -> None:
    service = make_service()
    service.select_all()

    ui, _ = make_ui(service, ["d", ""])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_count == 0


def test_ui_cancel_returns_none_without_changing_selection() -> None:
    service = make_service()
    service.select("src/auth.py")

    ui, output = make_ui(service, ["q"])

    result = ui.run()

    assert result is None
    assert service.get_selection().selected_paths == ("src/auth.py",)
    assert "Selection cancelled." in output.getvalue()


def test_ui_rejects_invalid_file_number_without_changing_selection() -> None:
    service = make_service()
    ui, output = make_ui(service, ["9", ""])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_count == 0
    assert "Invalid file number" in output.getvalue()


def test_ui_reports_unknown_command() -> None:
    service = make_service()
    ui, output = make_ui(service, ["invalid", ""])

    ui.run()

    assert "Unknown command" in output.getvalue()


def test_ui_reports_navigation_boundaries() -> None:
    service = make_service()
    ui, output = make_ui(service, ["p", "n", "n", "n", ""])

    ui.run()

    rendered = output.getvalue()

    assert "first page" in rendered
    assert "last page" in rendered


def test_ui_cancels_on_end_of_input() -> None:
    service = make_service()
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None)

    def end_of_input(_prompt: str) -> str:
        raise EOFError

    ui = SelectionTerminalUI(
        service=service,
        console=console,
        input_provider=end_of_input,
    )

    assert ui.run() is None
    assert "Selection cancelled." in output.getvalue()


def test_ui_supports_empty_snapshot() -> None:
    service = FileSelectionService(GitStatusSnapshot(files=()))
    ui, output = make_ui(service, [""])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.total_count == 0
    assert result.selected_count == 0
    assert "Files: 0" in output.getvalue()


def test_ui_rejects_invalid_service() -> None:
    with pytest.raises(TypeError, match="FileSelectionService"):
        SelectionTerminalUI(None)  # type: ignore[arg-type]


def test_ui_returns_empty_snapshot_when_user_confirms_without_selection() -> None:
    service = make_service()
    ui, _ = make_ui(service, [""])

    result = ui.run()

    assert isinstance(result, FileSelectionSnapshot)
    assert result.selected_count == 0
