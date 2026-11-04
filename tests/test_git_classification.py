"""Tests for Git file classification."""

from gitmind.core.git.classification import GitChangeType, GitFileClassifier
from gitmind.core.git.status_models import GitFileStatus


def test_classify_staged_modification() -> None:
    file = GitFileStatus("src/app.py", "M", " ")
    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.MODIFIED,)


def test_classify_unstaged_modification() -> None:
    file = GitFileStatus("src/app.py", " ", "M")
    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.MODIFIED,)


def test_classify_staged_addition() -> None:
    file = GitFileStatus("src/new.py", "A", " ")
    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.ADDED,)


def test_classify_untracked_file_separately() -> None:
    file = GitFileStatus("src/new.py", "?", "?")
    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.UNTRACKED,)
    assert GitChangeType.ADDED not in result


def test_classify_deleted_file() -> None:
    file = GitFileStatus("src/old.py", "D", " ")
    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.DELETED,)


def test_classify_renamed_file() -> None:
    file = GitFileStatus(
        path="src/new.py",
        index_status="R",
        worktree_status=" ",
        original_path="src/old.py",
    )

    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.RENAMED,)


def test_classify_copied_file() -> None:
    file = GitFileStatus(
        path="src/copied.py",
        index_status="C",
        worktree_status=" ",
        original_path="src/original.py",
    )

    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.COPIED,)


def test_classify_type_changed_file() -> None:
    file = GitFileStatus("src/tool", "T", " ")
    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.TYPE_CHANGED,)


def test_classify_unmerged_file() -> None:
    file = GitFileStatus("src/conflict.py", "U", "U")
    result = GitFileClassifier().classify(file)

    assert result == (GitChangeType.UNMERGED,)


def test_classify_mixed_changes_without_duplicates() -> None:
    file = GitFileStatus("src/app.py", "A", "M")
    result = GitFileClassifier().classify(file)

    assert result == (
        GitChangeType.ADDED,
        GitChangeType.MODIFIED,
    )


def test_classify_preserves_staging_information() -> None:
    file = GitFileStatus("src/app.py", "M", "M")
    classifier = GitFileClassifier()

    result = classifier.classify(file)

    assert result == (GitChangeType.MODIFIED,)
    assert file.is_staged
    assert file.is_unstaged


def test_change_type_is_string_compatible() -> None:
    change_type = GitChangeType.MODIFIED

    assert isinstance(change_type, str)
    assert change_type.value == "modified"
    assert str(change_type) == "modified"
