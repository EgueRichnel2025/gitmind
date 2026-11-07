"""Service for safely staging selected Git files."""

from pathlib import Path, PurePosixPath, PureWindowsPath

from gitmind.core.git.runner import GitRunner
from gitmind.core.git.staging_errors import (
    EmptyGitStagingSelectionError,
    UnsafeGitPathError,
)
from gitmind.core.git.staging_models import GitStagingResult
from gitmind.core.selection.models import FileSelectionSnapshot


class GitStagingService:
    """Stage only the files explicitly selected by the user."""

    def __init__(
        self,
        repository_root: str | Path,
        runner: GitRunner | None = None,
    ) -> None:
        root = Path(repository_root)

        if not root.exists():
            raise FileNotFoundError(f"Repository directory does not exist: {root}")

        if not root.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {root}")

        self._repository_root = root.resolve()
        self._runner = runner if runner is not None else GitRunner()

    def stage(
        self,
        selection: FileSelectionSnapshot,
    ) -> GitStagingResult:
        """Stage exactly the selected files without touching other paths."""
        if not isinstance(selection, FileSelectionSnapshot):
            raise TypeError("selection must be a FileSelectionSnapshot instance.")

        if not selection.has_selection:
            raise EmptyGitStagingSelectionError()

        selected_paths = selection.selected_paths

        # Validate every path before executing any Git command.
        for path in selected_paths:
            self._validate_path(path)

        pathspecs = tuple(f":(literal){path}" for path in selected_paths)

        self._runner.run(
            "add",
            "--all",
            "--",
            *pathspecs,
            cwd=self._repository_root,
        )

        return GitStagingResult(
            selected_paths=selected_paths,
            affected_paths=selected_paths,
        )

    @staticmethod
    def _validate_path(path: str) -> None:
        """Reject absolute paths and path traversal."""
        if not isinstance(path, str):
            raise UnsafeGitPathError(
                str(path),
                "File path must be a string.",
            )

        if not path or "\0" in path:
            raise UnsafeGitPathError(
                path,
                "File path cannot be empty or contain NUL characters.",
            )

        posix_path = PurePosixPath(path)
        windows_path = PureWindowsPath(path)

        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or windows_path.root
        ):
            raise UnsafeGitPathError(
                path,
                "Absolute paths are not allowed.",
            )

        normalized_path = path.replace("\\", "/")
        components = normalized_path.split("/")

        if any(component in {"", ".", ".."} for component in components):
            raise UnsafeGitPathError(
                path,
                "Path traversal or non-canonical path components are not allowed.",
            )
