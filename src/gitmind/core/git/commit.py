"""Service for safely committing only selected staged files."""

from pathlib import Path, PurePosixPath, PureWindowsPath

from gitmind.core.git.commit_errors import (
    EmptyGitCommitSelectionError,
    GitCommitSelectionHasUnstagedChangesError,
    GitCommitSelectionNotStagedError,
    GitCommitSelectionUnmergedError,
    InvalidGitCommitMessageError,
    UnsafeGitCommitPathError,
)
from gitmind.core.git.commit_models import GitCommitResult
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.status_service import GitStatusService
from gitmind.core.selection.models import FileSelectionSnapshot


class GitCommitService:
    """Commit only explicitly selected files while preserving other staged changes."""

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
        self._status_service = GitStatusService(runner=self._runner)

    def commit(
        self,
        selection: FileSelectionSnapshot,
        message: str,
    ) -> GitCommitResult:
        """Commit exactly the selected staged files."""
        if not isinstance(selection, FileSelectionSnapshot):
            raise TypeError("selection must be a FileSelectionSnapshot instance.")

        if not selection.has_selection:
            raise EmptyGitCommitSelectionError()

        self._validate_message(message)

        # Validate selected paths before retrieving or changing repository state.
        for path in selection.selected_paths:
            self._validate_path(path)

        current_status = self._status_service.get_status(self._repository_root)
        status_by_path = {git_file.path: git_file for git_file in current_status.files}

        affected_paths: list[str] = []

        # Revalidate every selected file against the current repository state.
        for selectable_file in selection.selected_files:
            path = selectable_file.path
            git_file = status_by_path.get(path)

            if git_file is None or not git_file.is_staged:
                raise GitCommitSelectionNotStagedError(path)

            if git_file.is_unmerged:
                raise GitCommitSelectionUnmergedError(path)

            if git_file.is_unstaged:
                raise GitCommitSelectionHasUnstagedChangesError(path)

            affected_paths.append(path)

            # A rename is represented by its new path and its original path.
            if git_file.original_path is not None:
                self._validate_path(git_file.original_path)
                affected_paths.append(git_file.original_path)

        # Preserve order while removing duplicate paths.
        unique_paths = tuple(dict.fromkeys(affected_paths))

        # Literal pathspecs prevent special characters from being interpreted
        # as Git pathspec patterns.
        pathspecs = tuple(f":(literal){path}" for path in unique_paths)

        self._runner.run(
            "commit",
            "--only",
            "-m",
            message,
            "--",
            *pathspecs,
            cwd=self._repository_root,
        )

        commit_result = self._runner.run(
            "rev-parse",
            "HEAD",
            cwd=self._repository_root,
        )

        return GitCommitResult(
            commit_hash=commit_result.stdout.strip(),
            message=message,
            committed_paths=selection.selected_paths,
        )

    @staticmethod
    def _validate_message(message: str) -> None:
        """Reject invalid single-line commit messages."""
        if not isinstance(message, str):
            raise TypeError("message must be a string.")

        if not message.strip() or "\0" in message:
            raise InvalidGitCommitMessageError(
                "Commit message cannot be empty or contain NUL characters."
            )

        if "\n" in message or "\r" in message:
            raise InvalidGitCommitMessageError("Commit message must contain only one line.")

        if message != message.strip():
            raise InvalidGitCommitMessageError("Commit message cannot have surrounding whitespace.")

    @staticmethod
    def _validate_path(path: str) -> None:
        """Reject absolute paths and path traversal."""
        if not isinstance(path, str):
            raise UnsafeGitCommitPathError(
                str(path),
                "File path must be a string.",
            )

        if not path or "\0" in path:
            raise UnsafeGitCommitPathError(
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
            raise UnsafeGitCommitPathError(
                path,
                "Absolute paths are not allowed.",
            )

        normalized_path = path.replace("\\", "/")
        components = normalized_path.split("/")

        if any(component in {"", ".", ".."} for component in components):
            raise UnsafeGitCommitPathError(
                path,
                "Path traversal or non-canonical path components are not allowed.",
            )
