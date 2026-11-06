"""Tests for immutable Git file difference models."""

import pytest

from gitmind.core.analysis import FileDiff


def test_file_diff_accepts_default_values() -> None:
    result = FileDiff(path="src/main.py")

    assert result.staged_diff == ""
    assert result.unstaged_diff == ""
    assert result.staged_diff_truncated is False
    assert result.unstaged_diff_truncated is False


def test_file_diff_preserves_separate_diffs() -> None:
    result = FileDiff(
        path="src/main.py",
        staged_diff="staged changes",
        unstaged_diff="unstaged changes",
    )

    assert result.staged_diff == "staged changes"
    assert result.unstaged_diff == "unstaged changes"


def test_file_diff_exposes_diff_presence() -> None:
    result = FileDiff(
        path="src/main.py",
        staged_diff="staged changes",
    )

    assert result.has_staged_diff is True
    assert result.has_unstaged_diff is False
    assert result.has_diff is True


def test_file_diff_reports_truncation() -> None:
    result = FileDiff(
        path="src/main.py",
        staged_diff="partial staged diff",
        staged_diff_truncated=True,
    )

    assert result.is_truncated is True


def test_file_diff_is_not_truncated_by_default() -> None:
    result = FileDiff(path="src/main.py")

    assert result.is_truncated is False


@pytest.mark.parametrize("path", ["", "src/\0main.py"])
def test_file_diff_rejects_invalid_paths(path: str) -> None:
    with pytest.raises(ValueError):
        FileDiff(path=path)


def test_file_diff_rejects_non_string_path() -> None:
    with pytest.raises(TypeError):
        FileDiff(path=123)  # type: ignore[arg-type]


@pytest.mark.parametrize("field_name", ["staged_diff", "unstaged_diff"])
def test_file_diff_rejects_non_string_diffs(field_name: str) -> None:
    with pytest.raises(TypeError):
        FileDiff(
            path="src/main.py",
            **{field_name: 123},
        )


@pytest.mark.parametrize(
    "field_name",
    ["staged_diff_truncated", "unstaged_diff_truncated"],
)
def test_file_diff_rejects_non_boolean_truncation_flags(
    field_name: str,
) -> None:
    with pytest.raises(TypeError):
        FileDiff(
            path="src/main.py",
            **{field_name: 1},
        )


def test_file_diff_rejects_empty_truncated_staged_diff() -> None:
    with pytest.raises(ValueError):
        FileDiff(
            path="src/main.py",
            staged_diff_truncated=True,
        )


def test_file_diff_rejects_empty_truncated_unstaged_diff() -> None:
    with pytest.raises(ValueError):
        FileDiff(
            path="src/main.py",
            unstaged_diff_truncated=True,
        )
