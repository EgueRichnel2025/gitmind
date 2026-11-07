"""Git integration layer for GitMind."""

from gitmind.core.git.commit import GitCommitService
from gitmind.core.git.commit_errors import (
    EmptyGitCommitSelectionError,
    GitCommitError,
    GitCommitSelectionHasUnstagedChangesError,
    GitCommitSelectionNotStagedError,
    GitCommitSelectionUnmergedError,
    InvalidGitCommitMessageError,
    UnsafeGitCommitPathError,
)
from gitmind.core.git.commit_models import GitCommitResult
from gitmind.core.git.staging import GitStagingService
from gitmind.core.git.staging_errors import (
    EmptyGitStagingSelectionError,
    GitStagingError,
    UnsafeGitPathError,
)
from gitmind.core.git.staging_models import GitStagingResult

__all__ = [
    "EmptyGitCommitSelectionError",
    "EmptyGitStagingSelectionError",
    "GitCommitError",
    "GitCommitResult",
    "GitCommitSelectionHasUnstagedChangesError",
    "GitCommitSelectionNotStagedError",
    "GitCommitSelectionUnmergedError",
    "GitCommitService",
    "GitStagingError",
    "GitStagingResult",
    "GitStagingService",
    "InvalidGitCommitMessageError",
    "UnsafeGitCommitPathError",
    "UnsafeGitPathError",
]
