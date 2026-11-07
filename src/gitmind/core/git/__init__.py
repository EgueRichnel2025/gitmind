"""Git integration layer for GitMind."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "EmptyGitCommitSelectionError": (
        "commit_errors",
        "EmptyGitCommitSelectionError",
    ),
    "GitCommitError": ("commit_errors", "GitCommitError"),
    "GitCommitResult": ("commit_models", "GitCommitResult"),
    "GitCommitSelectionHasUnstagedChangesError": (
        "commit_errors",
        "GitCommitSelectionHasUnstagedChangesError",
    ),
    "GitCommitSelectionNotStagedError": (
        "commit_errors",
        "GitCommitSelectionNotStagedError",
    ),
    "GitCommitSelectionUnmergedError": (
        "commit_errors",
        "GitCommitSelectionUnmergedError",
    ),
    "GitCommitService": ("commit", "GitCommitService"),
    "EmptyGitStagingSelectionError": (
        "staging_errors",
        "EmptyGitStagingSelectionError",
    ),
    "GitStagingError": ("staging_errors", "GitStagingError"),
    "GitStagingResult": ("staging_models", "GitStagingResult"),
    "GitStagingService": ("staging", "GitStagingService"),
    "InvalidGitCommitMessageError": (
        "commit_errors",
        "InvalidGitCommitMessageError",
    ),
    "UnsafeGitCommitPathError": (
        "commit_errors",
        "UnsafeGitCommitPathError",
    ),
    "GitPushDetachedHeadError": (
        "push_errors",
        "GitPushDetachedHeadError",
    ),
    "GitPushError": ("push_errors", "GitPushError"),
    "GitPushRemoteNotFoundError": (
        "push_errors",
        "GitPushRemoteNotFoundError",
    ),
    "GitPushResult": ("push_models", "GitPushResult"),
    "GitPushService": ("push", "GitPushService"),
    "UnsafeGitPathError": ("staging_errors", "UnsafeGitPathError"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load public Git components only when they are requested."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _EXPORTS[name]
    module = import_module(f".{module_name}", package=__name__)
    value = getattr(module, attribute_name)

    # Cache the resolved object for subsequent imports.
    globals()[name] = value

    return value


def __dir__() -> list[str]:
    """Return the available public Git components."""
    return sorted(set(globals()) | set(__all__))
