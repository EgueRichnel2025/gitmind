"""Tests for Git repository status summaries."""

from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot
from gitmind.core.git.summary import GitStatusSummarizer


def create_complex_snapshot() -> GitStatusSnapshot:
    """Create a snapshot containing different Git file states."""
    return GitStatusSnapshot(
        files=(
            GitFileStatus("modified.py", " ", "M"),
            GitFileStatus("staged.py", "M", " "),
            GitFileStatus("added.py", "A", " "),
            GitFileStatus("mixed.py", "A", "M"),
            GitFileStatus("untracked.py", "?", "?"),
            GitFileStatus("deleted.py", "D", " "),
            GitFileStatus(
                "renamed.py",
                "R",
                " ",
                original_path="old_name.py",
            ),
            GitFileStatus(
                "copied.py",
                "C",
                " ",
                original_path="original.py",
            ),
            GitFileStatus("type_changed", "T", " "),
            GitFileStatus("conflict.py", "U", "U"),
            GitFileStatus("ignored.py", "!", "!"),
        )
    )


def test_summarize_empty_repository() -> None:
    snapshot = GitStatusSnapshot(files=())

    summary = GitStatusSummarizer().summarize(snapshot)

    assert summary.total_files == 0
    assert summary.has_changes is False
    assert summary.staged_files == 0
    assert summary.unstaged_files == 0


def test_summarize_all_change_categories() -> None:
    snapshot = create_complex_snapshot()

    summary = GitStatusSummarizer().summarize(snapshot)

    assert summary.total_files == 11
    assert summary.modified_files == 3
    assert summary.added_files == 2
    assert summary.deleted_files == 1
    assert summary.renamed_files == 1
    assert summary.copied_files == 1
    assert summary.type_changed_files == 1
    assert summary.unmerged_files == 1
    assert summary.untracked_files == 1
    assert summary.ignored_files == 1


def test_summarize_staged_and_unstaged_states() -> None:
    snapshot = create_complex_snapshot()

    summary = GitStatusSummarizer().summarize(snapshot)

    assert summary.staged_files == 8
    assert summary.unstaged_files == 4


def test_summarize_mixed_file_without_duplicating_total() -> None:
    snapshot = GitStatusSnapshot(files=(GitFileStatus("mixed.py", "A", "M"),))

    summary = GitStatusSummarizer().summarize(snapshot)

    assert summary.total_files == 1
    assert summary.added_files == 1
    assert summary.modified_files == 1


def test_summarize_untracked_and_added_files_separately() -> None:
    snapshot = GitStatusSnapshot(
        files=(
            GitFileStatus("added.py", "A", " "),
            GitFileStatus("new.py", "?", "?"),
        )
    )

    summary = GitStatusSummarizer().summarize(snapshot)

    assert summary.total_files == 2
    assert summary.added_files == 1
    assert summary.untracked_files == 1


def test_summary_reports_changes() -> None:
    snapshot = GitStatusSnapshot(files=(GitFileStatus("app.py", " ", "M"),))

    summary = GitStatusSummarizer().summarize(snapshot)

    assert summary.has_changes is True
