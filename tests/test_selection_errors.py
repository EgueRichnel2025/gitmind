"""Tests for file selection exceptions."""

import pytest

from gitmind.core.selection.errors import (
    FileNotFoundInSelectionError,
    FileSelectionError,
)


def test_file_selection_error_is_a_runtime_error() -> None:
    error = FileSelectionError("Selection failed")

    assert isinstance(error, RuntimeError)
    assert str(error) == "Selection failed"


def test_file_not_found_error_inherits_from_selection_error() -> None:
    error = FileNotFoundInSelectionError("src/missing.py")

    assert isinstance(error, FileSelectionError)
    assert isinstance(error, RuntimeError)


def test_file_not_found_error_preserves_file_path() -> None:
    path = "src/missing.py"
    error = FileNotFoundInSelectionError(path)

    assert error.path == path
    assert path in str(error)
    assert "not available" in str(error)
