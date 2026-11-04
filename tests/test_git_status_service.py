"""Integration tests for GitStatusService."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.git.errors import GitRepositoryNotFoundError
from gitmind.core.git.status_service import GitStatusService


def run_git(*args: str, cwd: Path) -> None:
    """Execute a Git command in a test repository."""
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a temporary Git repository with a local identity."""
    path = tmp_path / "project with spaces"
    path.mkdir()

    run_git("init", cwd=path)
    run_git("config", "user.name", "GitMind Tests", cwd=path)
    run_git("config", "user.email", "tests@gitmind.dev", cwd=path)

    return path.resolve()


def create_commit(repository: Path, filename: str, content: str) -> None:
    """Create and commit a file."""
    file_path = repository / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    run_git("add", filename, cwd=repository)
    run_git("commit", "-m", "test: add initial file", cwd=repository)


def test_get_status_returns_clean_snapshot(repository: Path) -> None:
    create_commit(repository, "README.md", "# GitMind")

    service = GitStatusService()
    snapshot = service.get_status(repository)

    assert snapshot.is_clean
    assert snapshot.file_count == 0


def test_get_status_detects_untracked_files(repository: Path) -> None:
    file_path = repository / "src" / "new module.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("print('GitMind')", encoding="utf-8")

    service = GitStatusService()
    snapshot = service.get_status(repository)

    assert snapshot.file_count == 1
    assert snapshot.files[0].path == "src/new module.py"
    assert snapshot.files[0].is_untracked


def test_get_status_detects_unstaged_modifications(repository: Path) -> None:
    create_commit(repository, "src/app.py", "VERSION = 1\n")

    file_path = repository / "src" / "app.py"
    file_path.write_text("VERSION = 2\n", encoding="utf-8")

    service = GitStatusService()
    snapshot = service.get_status(repository)

    assert snapshot.file_count == 1
    assert snapshot.files[0].status_code == " M"


def test_get_status_detects_staged_modifications(repository: Path) -> None:
    create_commit(repository, "src/app.py", "VERSION = 1\n")

    file_path = repository / "src" / "app.py"
    file_path.write_text("VERSION = 2\n", encoding="utf-8")

    run_git("add", "src/app.py", cwd=repository)

    service = GitStatusService()
    snapshot = service.get_status(repository)

    assert snapshot.file_count == 1
    assert snapshot.files[0].status_code == "M "


def test_get_status_preserves_staged_and_unstaged_changes(
    repository: Path,
) -> None:
    create_commit(repository, "src/app.py", "VERSION = 1\n")

    file_path = repository / "src" / "app.py"

    file_path.write_text("VERSION = 2\n", encoding="utf-8")
    run_git("add", "src/app.py", cwd=repository)

    file_path.write_text("VERSION = 3\n", encoding="utf-8")

    service = GitStatusService()
    snapshot = service.get_status(repository)

    assert snapshot.file_count == 1
    assert snapshot.files[0].status_code == "MM"
    assert snapshot.files[0].is_staged
    assert snapshot.files[0].is_unstaged


def test_get_status_detects_all_untracked_nested_files(
    repository: Path,
) -> None:
    first_file = repository / "src" / "auth" / "login.py"
    second_file = repository / "src" / "auth" / "register.py"

    first_file.parent.mkdir(parents=True)
    first_file.write_text("login()", encoding="utf-8")
    second_file.write_text("register()", encoding="utf-8")

    service = GitStatusService()
    snapshot = service.get_status(repository)

    paths = {file.path for file in snapshot.files}

    assert snapshot.file_count == 2
    assert paths == {
        "src/auth/login.py",
        "src/auth/register.py",
    }


def test_get_status_works_from_nested_directory(repository: Path) -> None:
    nested_directory = repository / "src" / "services"
    nested_directory.mkdir(parents=True)

    file_path = nested_directory / "payment.py"
    file_path.write_text("process_payment()", encoding="utf-8")

    service = GitStatusService()
    snapshot = service.get_status(nested_directory)

    assert snapshot.file_count == 1
    assert snapshot.files[0].path == "src/services/payment.py"


def test_get_status_rejects_directory_outside_repository(
    tmp_path: Path,
) -> None:
    ordinary_directory = tmp_path / "ordinary"
    ordinary_directory.mkdir()

    service = GitStatusService()

    with pytest.raises(GitRepositoryNotFoundError):
        service.get_status(ordinary_directory)


def test_get_status_does_not_include_ignored_files(repository: Path) -> None:
    create_commit(repository, "README.md", "# GitMind")

    gitignore = repository / ".gitignore"
    gitignore.write_text("build/\n", encoding="utf-8")

    run_git("add", ".gitignore", cwd=repository)
    run_git("commit", "-m", "test: add ignore rules", cwd=repository)

    ignored_directory = repository / "build"
    ignored_directory.mkdir()
    (ignored_directory / "generated.py").write_text(
        "generated = True",
        encoding="utf-8",
    )

    service = GitStatusService()
    snapshot = service.get_status(repository)

    assert snapshot.is_clean
