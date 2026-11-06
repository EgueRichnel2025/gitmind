"""Integration tests for FileAnalysisService."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.analysis import FileAnalysisService
from gitmind.core.git.status_service import GitStatusService
from gitmind.core.selection.models import (
    FileSelectionSnapshot,
    SelectableFile,
)


def run_git(*args: str, cwd: Path) -> str:
    """Execute a Git command in a test repository."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a temporary repository with a local Git identity."""
    path = tmp_path / "project with spaces"
    path.mkdir()

    run_git("init", cwd=path)
    run_git("config", "user.name", "GitMind Tests", cwd=path)
    run_git("config", "user.email", "tests@gitmind.dev", cwd=path)

    return path.resolve()


def create_commit(
    repository: Path,
    filename: str,
    content: str,
) -> None:
    """Create and commit a file."""
    file_path = repository / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content.encode("utf-8"))

    run_git("add", "--", filename, cwd=repository)
    run_git("commit", "-m", "test: add initial file", cwd=repository)


def make_selection(
    repository: Path,
    selected_paths: set[str],
) -> FileSelectionSnapshot:
    """Build a selection from the current Git status."""
    status = GitStatusService().get_status(repository)

    return FileSelectionSnapshot(
        files=tuple(
            SelectableFile(
                git_file=git_file,
                selected=git_file.path in selected_paths,
            )
            for git_file in status.files
        )
    )


def test_service_analyzes_only_selected_files(
    repository: Path,
) -> None:
    create_commit(repository, "first.py", "first = 1\n")
    create_commit(repository, "second.py", "second = 1\n")
    create_commit(repository, "third.py", "third = 1\n")

    (repository / "first.py").write_bytes(b"first = 2\n")
    (repository / "second.py").write_bytes(b"second = 2\n")
    (repository / "third.py").write_bytes(b"third = 2\n")

    selection = make_selection(
        repository,
        {"first.py", "second.py"},
    )

    result = FileAnalysisService(repository).analyze(selection)

    assert result.file_count == 2
    assert set(result.paths) == {"first.py", "second.py"}
    assert "third.py" not in result.paths


def test_service_preserves_selection_order(
    repository: Path,
) -> None:
    create_commit(repository, "first.py", "first = 1\n")
    create_commit(repository, "second.py", "second = 1\n")

    (repository / "first.py").write_bytes(b"first = 2\n")
    (repository / "second.py").write_bytes(b"second = 2\n")

    status = GitStatusService().get_status(repository)
    files = {file.path: file for file in status.files}

    selection = FileSelectionSnapshot(
        files=(
            SelectableFile(files["second.py"], selected=True),
            SelectableFile(files["first.py"], selected=True),
        )
    )

    result = FileAnalysisService(repository).analyze(selection)

    assert result.paths == ("second.py", "first.py")


def test_service_combines_staged_and_unstaged_diffs(
    repository: Path,
) -> None:
    create_commit(repository, "app.py", "VERSION = 1\n")

    file_path = repository / "app.py"

    file_path.write_bytes(b"VERSION = 2\n")
    run_git("add", "--", "app.py", cwd=repository)

    file_path.write_bytes(b"VERSION = 3\n")

    selection = make_selection(repository, {"app.py"})
    result = FileAnalysisService(repository).analyze(selection)

    analysis = result.files[0]

    assert analysis.status_code == "MM"
    assert "VERSION = 1" in analysis.staged_diff
    assert "VERSION = 2" in analysis.staged_diff
    assert "VERSION = 2" in analysis.unstaged_diff
    assert "VERSION = 3" in analysis.unstaged_diff
    assert analysis.content == "VERSION = 3\n"
    assert analysis.has_staged_diff
    assert analysis.has_unstaged_diff


def test_service_analyzes_untracked_file_content(
    repository: Path,
) -> None:
    (repository / "new_file.py").write_bytes(b"new_feature = True\n")

    selection = make_selection(repository, {"new_file.py"})
    result = FileAnalysisService(repository).analyze(selection)

    analysis = result.files[0]

    assert analysis.path == "new_file.py"
    assert analysis.content == "new_feature = True\n"
    assert analysis.size_bytes == len(b"new_feature = True\n")
    assert not analysis.has_diff


def test_service_handles_deleted_files(
    repository: Path,
) -> None:
    create_commit(repository, "obsolete.py", "obsolete = True\n")
    (repository / "obsolete.py").unlink()

    selection = make_selection(repository, {"obsolete.py"})
    result = FileAnalysisService(repository).analyze(selection)

    analysis = result.files[0]

    assert analysis.content is None
    assert analysis.size_bytes is None
    assert analysis.has_staged_diff is False
    assert analysis.has_unstaged_diff
    assert "obsolete = True" in analysis.unstaged_diff


def test_service_detects_binary_files(
    repository: Path,
) -> None:
    create_commit(repository, "image.bin", "initial content\n")

    (repository / "image.bin").write_bytes(b"\x89PNG\x00\x01\x02")

    selection = make_selection(repository, {"image.bin"})
    result = FileAnalysisService(repository).analyze(selection)

    analysis = result.files[0]

    assert analysis.is_binary
    assert analysis.content is None
    assert analysis.size_bytes == 7


def test_service_returns_empty_snapshot_for_empty_selection(
    repository: Path,
) -> None:
    create_commit(repository, "app.py", "value = 1\n")
    (repository / "app.py").write_bytes(b"value = 2\n")

    selection = make_selection(repository, set())
    result = FileAnalysisService(repository).analyze(selection)

    assert result.is_empty
    assert result.file_count == 0
    assert result.paths == ()


def test_service_does_not_modify_git_repository(
    repository: Path,
) -> None:
    create_commit(repository, "app.py", "VERSION = 1\n")

    file_path = repository / "app.py"

    file_path.write_bytes(b"VERSION = 2\n")
    run_git("add", "--", "app.py", cwd=repository)

    file_path.write_bytes(b"VERSION = 3\n")

    before = run_git(
        "status",
        "--porcelain=v1",
        "-z",
        cwd=repository,
    )

    selection = make_selection(repository, {"app.py"})
    FileAnalysisService(repository).analyze(selection)

    after = run_git(
        "status",
        "--porcelain=v1",
        "-z",
        cwd=repository,
    )

    assert after == before


def test_service_rejects_invalid_selection(
    repository: Path,
) -> None:
    service = FileAnalysisService(repository)

    with pytest.raises(TypeError):
        service.analyze(None)  # type: ignore[arg-type]
