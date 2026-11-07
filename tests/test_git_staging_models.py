"""Tests for Git staging models and errors."""

import pytest

from gitmind.core.git.staging_errors import (
    EmptyGitStagingSelectionError,
    GitStagingError,
    UnsafeGitPathError,
)
from gitmind.core.git.staging_models import GitStagingResult


def test_staging_result_stores_paths() -> None:
    result = GitStagingResult(
        selected_paths=("src/app.py", "README.md"),
        affected_paths=("src/app.py", "README.md"),
    )

    assert result.selected_paths == ("src/app.py", "README.md")
    assert result.affected_paths == ("src/app.py", "README.md")


def test_staging_result_exposes_counts() -> None:
    result = GitStagingResult(
        selected_paths=("src/app.py",),
        affected_paths=("src/app.py", "src/old_app.py"),
    )

    assert result.selected_count == 1
    assert result.affected_count == 2


def test_staging_result_rejects_empty_selection() -> None:
    with pytest.raises(ValueError, match="selected_paths cannot be empty"):
        GitStagingResult(
            selected_paths=(),
            affected_paths=(),
        )


def test_staging_result_rejects_duplicate_selected_paths() -> None:
    with pytest.raises(ValueError, match="Duplicate selected paths"):
        GitStagingResult(
            selected_paths=("app.py", "app.py"),
            affected_paths=("app.py",),
        )


def test_staging_result_rejects_duplicate_affected_paths() -> None:
    with pytest.raises(ValueError, match="Duplicate affected paths"):
        GitStagingResult(
            selected_paths=("app.py",),
            affected_paths=("app.py", "app.py"),
        )


def test_staging_result_requires_selected_paths_in_affected_paths() -> None:
    with pytest.raises(ValueError, match="included in affected_paths"):
        GitStagingResult(
            selected_paths=("app.py",),
            affected_paths=("README.md",),
        )


def test_staging_result_rejects_invalid_path_types() -> None:
    with pytest.raises(TypeError, match="All paths must be strings"):
        GitStagingResult(
            selected_paths=(123,),  # type: ignore[arg-type]
            affected_paths=("app.py",),
        )


def test_staging_result_requires_tuples() -> None:
    with pytest.raises(TypeError, match="selected_paths must be a tuple"):
        GitStagingResult(
            selected_paths=["app.py"],  # type: ignore[arg-type]
            affected_paths=("app.py",),
        )


def test_staging_error_hierarchy() -> None:
    assert issubclass(EmptyGitStagingSelectionError, GitStagingError)
    assert issubclass(UnsafeGitPathError, GitStagingError)


def test_empty_selection_error_message() -> None:
    error = EmptyGitStagingSelectionError()

    assert "selection is empty" in str(error)


def test_unsafe_path_error_preserves_details() -> None:
    error = UnsafeGitPathError("../outside.txt", "Path traversal is not allowed.")

    assert error.path == "../outside.txt"
    assert error.reason == "Path traversal is not allowed."
    assert "../outside.txt" in str(error)
