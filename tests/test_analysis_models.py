"""Tests for GitMind file analysis data models."""

import pytest

from gitmind.core.analysis import FileAnalysis, FileAnalysisSnapshot
from gitmind.core.git.status_models import GitFileStatus


def make_git_file(
    path: str = "src/main.py",
    index_status: str = " ",
    worktree_status: str = "M",
) -> GitFileStatus:
    """Create a Git file status for testing."""
    return GitFileStatus(
        path=path,
        index_status=index_status,
        worktree_status=worktree_status,
    )


def make_analysis(
    path: str = "src/main.py",
    staged_diff: str = "",
    unstaged_diff: str = "",
    content: str | None = None,
    **kwargs,
) -> FileAnalysis:
    """Create a file analysis result for testing."""
    return FileAnalysis(
        git_file=make_git_file(path=path),
        staged_diff=staged_diff,
        unstaged_diff=unstaged_diff,
        content=content,
        **kwargs,
    )


def test_file_analysis_accepts_default_values() -> None:
    analysis = make_analysis()

    assert analysis.path == "src/main.py"
    assert analysis.status_code == " M"
    assert analysis.staged_diff == ""
    assert analysis.unstaged_diff == ""
    assert analysis.content is None
    assert analysis.is_binary is False
    assert analysis.size_bytes is None


def test_file_analysis_exposes_git_file_metadata() -> None:
    analysis = FileAnalysis(
        git_file=GitFileStatus(
            path="src/new_name.py",
            index_status="R",
            worktree_status=" ",
            original_path="src/old_name.py",
        )
    )

    assert analysis.path == "src/new_name.py"
    assert analysis.original_path == "src/old_name.py"
    assert analysis.status_code == "R "


def test_file_analysis_keeps_staged_and_unstaged_diffs_separate() -> None:
    analysis = make_analysis(
        staged_diff="staged changes",
        unstaged_diff="unstaged changes",
    )

    assert analysis.has_staged_diff is True
    assert analysis.has_unstaged_diff is True
    assert analysis.has_diff is True


def test_file_analysis_accepts_empty_text_content() -> None:
    analysis = make_analysis(content="", size_bytes=0)

    assert analysis.has_content is True
    assert analysis.content == ""
    assert analysis.size_bytes == 0


def test_file_analysis_identifies_binary_content() -> None:
    analysis = make_analysis(
        is_binary=True,
        size_bytes=1024,
    )

    assert analysis.is_binary is True
    assert analysis.has_content is False


def test_file_analysis_reports_content_truncation() -> None:
    analysis = make_analysis(
        content="partial content",
        content_truncated=True,
    )

    assert analysis.content_truncated is True
    assert analysis.has_content is True


def test_file_analysis_reports_diff_truncation() -> None:
    analysis = make_analysis(
        staged_diff="partial staged diff",
        staged_diff_truncated=True,
    )

    assert analysis.diff_truncated is True


def test_file_analysis_rejects_invalid_git_file() -> None:
    with pytest.raises(TypeError, match="GitFileStatus"):
        FileAnalysis(git_file=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("staged_diff", None),
        ("unstaged_diff", None),
        ("content", 123),
    ],
)
def test_file_analysis_rejects_invalid_text_fields(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError):
        make_analysis(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "is_binary",
        "content_truncated",
        "staged_diff_truncated",
        "unstaged_diff_truncated",
    ],
)
def test_file_analysis_requires_boolean_flags(field_name: str) -> None:
    with pytest.raises(TypeError, match="must be a boolean"):
        make_analysis(**{field_name: "yes"})


def test_file_analysis_rejects_text_content_for_binary_files() -> None:
    with pytest.raises(ValueError, match="Binary files"):
        make_analysis(
            content="some text",
            is_binary=True,
        )


def test_file_analysis_rejects_truncated_content_when_content_is_missing() -> None:
    with pytest.raises(ValueError, match="must not be None"):
        make_analysis(content_truncated=True)


def test_file_analysis_rejects_non_integer_size() -> None:
    with pytest.raises(TypeError, match="size_bytes"):
        make_analysis(size_bytes=12.5)


def test_file_analysis_rejects_boolean_size() -> None:
    with pytest.raises(TypeError, match="size_bytes"):
        make_analysis(size_bytes=True)


def test_file_analysis_rejects_negative_size() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        make_analysis(size_bytes=-1)


def test_analysis_snapshot_accepts_empty_collection() -> None:
    snapshot = FileAnalysisSnapshot(files=())

    assert snapshot.file_count == 0
    assert snapshot.is_empty is True
    assert snapshot.paths == ()
    assert snapshot.has_diffs is False


def test_analysis_snapshot_preserves_file_order() -> None:
    first = make_analysis(path="src/auth.py")
    second = make_analysis(path="src/main.py")

    snapshot = FileAnalysisSnapshot(files=(first, second))

    assert snapshot.paths == ("src/auth.py", "src/main.py")
    assert snapshot.file_count == 2
    assert snapshot.is_empty is False


def test_analysis_snapshot_rejects_non_tuple_files() -> None:
    with pytest.raises(TypeError, match="must be a tuple"):
        FileAnalysisSnapshot(files=[])  # type: ignore[arg-type]


def test_analysis_snapshot_rejects_invalid_file_entries() -> None:
    with pytest.raises(TypeError, match="FileAnalysis"):
        FileAnalysisSnapshot(files=("src/main.py",))  # type: ignore[arg-type]


def test_analysis_snapshot_rejects_duplicate_paths() -> None:
    first = make_analysis(path="src/main.py")
    second = make_analysis(path="src/main.py")

    with pytest.raises(ValueError, match="Duplicate file paths"):
        FileAnalysisSnapshot(files=(first, second))


def test_analysis_snapshot_summarizes_analysis_results() -> None:
    staged = make_analysis(
        path="src/auth.py",
        staged_diff="staged patch",
        content="partial content",
        content_truncated=True,
        staged_diff_truncated=True,
    )

    unstaged = make_analysis(
        path="src/main.py",
        unstaged_diff="unstaged patch",
    )

    binary = make_analysis(
        path="assets/logo.png",
        is_binary=True,
    )

    snapshot = FileAnalysisSnapshot(files=(staged, unstaged, binary))

    assert snapshot.file_count == 3
    assert snapshot.staged_diff_count == 1
    assert snapshot.unstaged_diff_count == 1
    assert snapshot.binary_count == 1
    assert snapshot.content_truncated_count == 1
    assert snapshot.diff_truncated_count == 1
    assert snapshot.has_diffs is True
