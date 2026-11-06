"""Integration tests for GitDiffReader."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.analysis import GitDiffReader
from gitmind.core.analysis.content import UnsafeFilePathError
from gitmind.core.git.status_models import GitFileStatus


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
    """Create a temporary repository with a local Git identity."""
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
    file_path.write_bytes(content.encode("utf-8"))

    run_git("add", "--", filename, cwd=repository)
    run_git("commit", "-m", "test: add initial file", cwd=repository)


def test_reader_returns_staged_diff(repository: Path) -> None:
    create_commit(repository, "src/app.py", "VERSION = 1\n")

    file_path = repository / "src" / "app.py"
    file_path.write_bytes(b"VERSION = 2\n")
    run_git("add", "--", "src/app.py", cwd=repository)

    git_file = GitFileStatus("src/app.py", "M", " ")
    result = GitDiffReader(repository).read(git_file)

    assert "VERSION = 1" in result.staged_diff
    assert "VERSION = 2" in result.staged_diff
    assert result.unstaged_diff == ""
    assert result.has_staged_diff
    assert not result.has_unstaged_diff


def test_reader_returns_unstaged_diff(repository: Path) -> None:
    create_commit(repository, "src/app.py", "VERSION = 1\n")

    file_path = repository / "src" / "app.py"
    file_path.write_bytes(b"VERSION = 2\n")

    git_file = GitFileStatus("src/app.py", " ", "M")
    result = GitDiffReader(repository).read(git_file)

    assert "VERSION = 1" in result.unstaged_diff
    assert "VERSION = 2" in result.unstaged_diff
    assert result.staged_diff == ""
    assert result.has_unstaged_diff
    assert not result.has_staged_diff


def test_reader_keeps_staged_and_unstaged_diffs_separate(
    repository: Path,
) -> None:
    create_commit(repository, "src/app.py", "VERSION = 1\n")

    file_path = repository / "src" / "app.py"

    file_path.write_bytes(b"VERSION = 2\n")
    run_git("add", "--", "src/app.py", cwd=repository)

    file_path.write_bytes(b"VERSION = 3\n")

    git_file = GitFileStatus("src/app.py", "M", "M")
    result = GitDiffReader(repository).read(git_file)

    assert "VERSION = 1" in result.staged_diff
    assert "VERSION = 2" in result.staged_diff

    assert "VERSION = 2" in result.unstaged_diff
    assert "VERSION = 3" in result.unstaged_diff

    assert result.has_staged_diff
    assert result.has_unstaged_diff


def test_reader_handles_staged_deletion(repository: Path) -> None:
    create_commit(repository, "obsolete.py", "obsolete = True\n")

    run_git("rm", "obsolete.py", cwd=repository)

    git_file = GitFileStatus("obsolete.py", "D", " ")
    result = GitDiffReader(repository).read(git_file)

    assert result.has_staged_diff
    assert "obsolete = True" in result.staged_diff
    assert result.unstaged_diff == ""


def test_reader_handles_untracked_files(repository: Path) -> None:
    file_path = repository / "new file.py"
    file_path.write_bytes(b"new_file = True\n")

    git_file = GitFileStatus("new file.py", "?", "?")
    result = GitDiffReader(repository).read(git_file)

    assert not result.has_diff


def test_reader_supports_paths_with_spaces_and_special_characters(
    repository: Path,
) -> None:
    filename = "src/[special] module.py"
    create_commit(repository, filename, "value = 1\n")

    (repository / filename).write_bytes(b"value = 2\n")

    git_file = GitFileStatus(filename, " ", "M")
    result = GitDiffReader(repository).read(git_file)

    assert result.has_unstaged_diff
    assert "value = 1" in result.unstaged_diff
    assert "value = 2" in result.unstaged_diff


def test_reader_handles_staged_rename(repository: Path) -> None:
    create_commit(repository, "old_name.py", "value = 1\n")

    run_git("mv", "old_name.py", "new_name.py", cwd=repository)

    git_file = GitFileStatus(
        path="new_name.py",
        index_status="R",
        worktree_status=" ",
        original_path="old_name.py",
    )

    result = GitDiffReader(repository).read(git_file)

    assert result.has_staged_diff
    assert "old_name.py" in result.staged_diff
    assert "new_name.py" in result.staged_diff


def test_reader_truncates_large_diffs(repository: Path) -> None:
    create_commit(repository, "large.txt", "old\n")

    large_content = "new value\n" * 100
    (repository / "large.txt").write_bytes(large_content.encode("utf-8"))

    git_file = GitFileStatus("large.txt", " ", "M")
    reader = GitDiffReader(repository, max_diff_size_bytes=100)

    result = reader.read(git_file)

    assert result.unstaged_diff_truncated
    assert len(result.unstaged_diff.encode("utf-8")) <= 100


def test_reader_rejects_unsafe_paths(repository: Path) -> None:
    reader = GitDiffReader(repository)

    git_file = GitFileStatus("../outside.txt", "M", " ")

    with pytest.raises(UnsafeFilePathError):
        reader.read(git_file)


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, True, 1.5, "100"],
)
def test_reader_rejects_invalid_diff_size_limit(
    repository: Path,
    invalid_limit: object,
) -> None:
    with pytest.raises(ValueError):
        GitDiffReader(
            repository,
            max_diff_size_bytes=invalid_limit,  # type: ignore[arg-type]
        )
