"""Tests for Git repository discovery."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.git.repository import RepositoryDetector, RepositoryInfo


def create_repository(path: Path) -> Path:
    """Create a real Git repository for testing."""
    path.mkdir(parents=True)

    subprocess.run(
        ["git", "init", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )

    return path.resolve()


def test_discover_repository_root(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "project")

    detector = RepositoryDetector()
    result = detector.discover(repository)

    assert result == RepositoryInfo(root=repository)


def test_discover_repository_from_nested_directory(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "project")

    nested_directory = repository / "src" / "auth"
    nested_directory.mkdir(parents=True)

    detector = RepositoryDetector()
    result = detector.discover(nested_directory)

    assert result is not None
    assert result.root == repository


def test_discover_returns_none_outside_repository(tmp_path: Path) -> None:
    directory = tmp_path / "ordinary-directory"
    directory.mkdir()

    detector = RepositoryDetector()
    result = detector.discover(directory)

    assert result is None


def test_discover_rejects_nonexistent_directory(tmp_path: Path) -> None:
    detector = RepositoryDetector()
    nonexistent = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        detector.discover(nonexistent)


def test_discover_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "README.md"
    file_path.write_text("GitMind test", encoding="utf-8")

    detector = RepositoryDetector()

    with pytest.raises(NotADirectoryError):
        detector.discover(file_path)


def test_is_repository_returns_correct_boolean(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "project")

    ordinary_directory = tmp_path / "ordinary"
    ordinary_directory.mkdir()

    detector = RepositoryDetector()

    assert detector.is_repository(repository) is True
    assert detector.is_repository(ordinary_directory) is False
