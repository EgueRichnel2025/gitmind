"""Read staged and unstaged Git differences safely."""

from pathlib import Path, PurePosixPath, PureWindowsPath

from gitmind.core.analysis.content import UnsafeFilePathError
from gitmind.core.analysis.diff_models import FileDiff
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.status_models import GitFileStatus


class GitDiffReader:
    """Retrieve staged and unstaged diffs for selected repository files."""

    def __init__(
        self,
        repository_root: str | Path,
        runner: GitRunner | None = None,
        max_diff_size_bytes: int = 500_000,
    ) -> None:
        if (
            isinstance(max_diff_size_bytes, bool)
            or not isinstance(max_diff_size_bytes, int)
            or max_diff_size_bytes <= 0
        ):
            raise ValueError("max_diff_size_bytes must be a positive integer.")

        root = Path(repository_root)

        if not root.exists():
            raise FileNotFoundError(f"Repository directory does not exist: {root}")

        if not root.is_dir():
            raise NotADirectoryError(f"Repository root is not a directory: {root}")

        self._root = root.resolve()
        self._runner = runner if runner is not None else GitRunner()
        self._max_diff_size_bytes = max_diff_size_bytes

    def read(self, git_file: GitFileStatus) -> FileDiff:
        """Read both Git diff areas for one selected file."""
        if not isinstance(git_file, GitFileStatus):
            raise TypeError("git_file must be a GitFileStatus instance.")

        paths = [git_file.path]

        if git_file.original_path is not None:
            paths.append(git_file.original_path)

        pathspecs = [self._build_literal_pathspec(path) for path in dict.fromkeys(paths)]

        # Untracked and ignored files have no Git diff.
        if git_file.is_untracked or git_file.is_ignored:
            return FileDiff(path=git_file.path)

        staged_diff = ""
        unstaged_diff = ""
        staged_truncated = False
        unstaged_truncated = False

        if git_file.is_staged:
            staged_diff = self._run_diff(
                pathspecs,
                staged=True,
            )
            staged_diff, staged_truncated = self._truncate(staged_diff)

        if git_file.is_unstaged:
            unstaged_diff = self._run_diff(
                pathspecs,
                staged=False,
            )
            unstaged_diff, unstaged_truncated = self._truncate(unstaged_diff)

        return FileDiff(
            path=git_file.path,
            staged_diff=staged_diff,
            unstaged_diff=unstaged_diff,
            staged_diff_truncated=staged_truncated,
            unstaged_diff_truncated=unstaged_truncated,
        )

    def _run_diff(
        self,
        pathspecs: list[str],
        staged: bool,
    ) -> str:
        """Execute a read-only Git diff command."""
        args = [
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "--find-renames",
            "--unified=3",
        ]

        if staged:
            args.append("--cached")

        args.extend(["--", *pathspecs])

        result = self._runner.run(
            *args,
            cwd=self._root,
        )

        return result.stdout

    def _build_literal_pathspec(self, relative_path: str) -> str:
        """Validate a repository path and make it a literal Git pathspec."""
        windows_path = PureWindowsPath(relative_path)
        posix_path = PurePosixPath(relative_path)

        if (
            not relative_path
            or posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or "\\" in relative_path
            or any(part in {"", ".", ".."} for part in relative_path.split("/"))
            or not posix_path.parts
        ):
            raise UnsafeFilePathError(f"Unsafe repository-relative file path: {relative_path!r}")

        return f":(literal){relative_path}"

    def _truncate(self, diff: str) -> tuple[str, bool]:
        """Limit the retained diff size while preserving valid UTF-8 text."""
        encoded = diff.encode("utf-8")

        if len(encoded) <= self._max_diff_size_bytes:
            return diff, False

        truncated = encoded[: self._max_diff_size_bytes].decode(
            "utf-8",
            errors="ignore",
        )

        return truncated, True
