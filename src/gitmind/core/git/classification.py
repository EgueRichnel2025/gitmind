"""Classification of Git file changes."""

from enum import StrEnum

from gitmind.core.git.status_models import GitFileStatus


class GitChangeType(StrEnum):
    """Supported categories of Git file changes."""

    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"
    TYPE_CHANGED = "type_changed"
    UNMERGED = "unmerged"
    UNTRACKED = "untracked"
    IGNORED = "ignored"


_STATUS_MAPPING = {
    "M": GitChangeType.MODIFIED,
    "A": GitChangeType.ADDED,
    "D": GitChangeType.DELETED,
    "R": GitChangeType.RENAMED,
    "C": GitChangeType.COPIED,
    "T": GitChangeType.TYPE_CHANGED,
    "U": GitChangeType.UNMERGED,
}


class GitFileClassifier:
    """Classify Git file changes independently from their staging state."""

    def classify(self, file: GitFileStatus) -> tuple[GitChangeType, ...]:
        """Return all distinct change categories associated with a file."""
        if file.is_untracked:
            return (GitChangeType.UNTRACKED,)

        if file.is_ignored:
            return (GitChangeType.IGNORED,)

        categories = dict.fromkeys(
            _STATUS_MAPPING[status]
            for status in (file.index_status, file.worktree_status)
            if status in _STATUS_MAPPING
        )

        return tuple(categories)
