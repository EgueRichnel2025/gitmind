"""Tests for Git linked worktree discovery."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.git.repository import RepositoryDetector, RepositoryInfo


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
def linked_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Create a repository and a linked worktree."""
    repository = tmp_path / "main-repository"
    repository.mkdir()

    run_git("init", cwd=repository)

    run_git("config", "user.name", "GitMind Tests", cwd=repository)
    run_git("config", "user.email", "tests@gitmind.dev", cwd=repository)

    readme = repository / "README.md"
    readme.write_text("# GitMind test repository\n", encoding="utf-8")

    run_git("add", "README.md", cwd=repository)
    run_git("commit", "-m", "test: initialize repository", cwd=repository)

    worktree = tmp_path / "linked-worktree"

    run_git(
        "worktree",
        "add",
        "--detach",
        str(worktree),
        "HEAD",
        cwd=repository,
    )

    return repository.resolve(), worktree.resolve()


def test_discover_linked_worktree_root(
    linked_worktree: tuple[Path, Path],
) -> None:
    repository, worktree = linked_worktree

    detector = RepositoryDetector()
    result = detector.discover(worktree)

    assert result == RepositoryInfo(root=worktree)
    assert result.root != repository


def test_discover_nested_directory_in_linked_worktree(
    linked_worktree: tuple[Path, Path],
) -> None:
    _, worktree = linked_worktree

    nested_directory = worktree / "src" / "git"
    nested_directory.mkdir(parents=True)

    detector = RepositoryDetector()
    result = detector.discover(nested_directory)

    assert result is not None
    assert result.root == worktree


def test_linked_worktree_is_recognized_as_repository(
    linked_worktree: tuple[Path, Path],
) -> None:
    _, worktree = linked_worktree

    detector = RepositoryDetector()

    assert detector.is_repository(worktree) is True
