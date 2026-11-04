"""Summary of Git repository changes."""

from dataclasses import dataclass

from gitmind.core.git.classification import GitChangeType, GitFileClassifier
from gitmind.core.git.status_models import GitStatusSnapshot


@dataclass(frozen=True, slots=True)
class GitStatusSummary:
    """Represent aggregated statistics for a Git status snapshot."""

    total_files: int
    modified_files: int
    added_files: int
    deleted_files: int
    renamed_files: int
    copied_files: int
    type_changed_files: int
    unmerged_files: int
    untracked_files: int
    ignored_files: int
    staged_files: int
    unstaged_files: int

    @property
    def has_changes(self) -> bool:
        """Return whether the repository contains reported files."""
        return self.total_files > 0


class GitStatusSummarizer:
    """Calculate repository statistics from a Git status snapshot."""

    def __init__(self, classifier: GitFileClassifier | None = None) -> None:
        self._classifier = classifier or GitFileClassifier()

    def summarize(self, snapshot: GitStatusSnapshot) -> GitStatusSummary:
        """Aggregate file classifications and staging information."""
        counts = {change_type: 0 for change_type in GitChangeType}

        for file in snapshot.files:
            for change_type in self._classifier.classify(file):
                counts[change_type] += 1

        return GitStatusSummary(
            total_files=snapshot.file_count,
            modified_files=counts[GitChangeType.MODIFIED],
            added_files=counts[GitChangeType.ADDED],
            deleted_files=counts[GitChangeType.DELETED],
            renamed_files=counts[GitChangeType.RENAMED],
            copied_files=counts[GitChangeType.COPIED],
            type_changed_files=counts[GitChangeType.TYPE_CHANGED],
            unmerged_files=counts[GitChangeType.UNMERGED],
            untracked_files=counts[GitChangeType.UNTRACKED],
            ignored_files=counts[GitChangeType.IGNORED],
            staged_files=snapshot.staged_count,
            unstaged_files=snapshot.unstaged_count,
        )
