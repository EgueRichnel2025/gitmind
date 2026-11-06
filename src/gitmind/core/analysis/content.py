"""Safe reading of repository working-tree file contents."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from gitmind.core.git.status_models import GitFileStatus


class UnsafeFilePathError(ValueError):
    """Raised when a repository-relative path is unsafe to read."""


class FileContentReadError(RuntimeError):
    """Raised when a file cannot be read safely."""


@dataclass(frozen=True, slots=True)
class FileContent:
    """Represent the content retrieved from a working-tree file."""

    content: str | None = None
    is_binary: bool = False
    content_truncated: bool = False
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("content must be a string or None.")

        if not isinstance(self.is_binary, bool):
            raise TypeError("is_binary must be a boolean.")

        if not isinstance(self.content_truncated, bool):
            raise TypeError("content_truncated must be a boolean.")

        if self.is_binary and self.content is not None:
            raise ValueError("Binary files cannot contain decoded text content.")

        if self.content_truncated and self.content is None:
            raise ValueError("Truncated content must not be None.")

        if self.size_bytes is not None:
            if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
                raise TypeError("size_bytes must be an integer or None.")

            if self.size_bytes < 0:
                raise ValueError("size_bytes cannot be negative.")


class WorkingTreeContentReader:
    """Read selected files without following links outside the repository."""

    def __init__(
        self,
        repository_root: str | Path,
        max_file_size_bytes: int = 1_000_000,
    ) -> None:
        if (
            isinstance(max_file_size_bytes, bool)
            or not isinstance(max_file_size_bytes, int)
            or max_file_size_bytes <= 0
        ):
            raise ValueError("max_file_size_bytes must be a positive integer.")

        root = Path(repository_root)

        if not root.exists():
            raise FileNotFoundError(f"Repository directory does not exist: {root}")

        if not root.is_dir():
            raise NotADirectoryError(f"Repository root is not a directory: {root}")

        self._root = root.resolve()
        self._max_file_size_bytes = max_file_size_bytes

    def read(self, git_file: GitFileStatus) -> FileContent:
        """Read the current working-tree content of a Git file."""
        if not isinstance(git_file, GitFileStatus):
            raise TypeError("git_file must be a GitFileStatus instance.")

        candidate = self._resolve_file_path(git_file.path)

        try:
            metadata = candidate.lstat()

            # Read the symbolic link itself, never its target.
            if stat.S_ISLNK(metadata.st_mode):
                raw_content = os.fsencode(os.readlink(candidate))
                return self._decode_content(
                    raw_content,
                    size_bytes=len(raw_content),
                )

            # Directories and special files do not provide regular text content.
            if not stat.S_ISREG(metadata.st_mode):
                return FileContent()

            with candidate.open("rb") as file:
                raw_content = file.read(self._max_file_size_bytes + 1)

            return self._decode_content(
                raw_content,
                size_bytes=metadata.st_size,
            )

        except FileNotFoundError:
            # Deleted files or paths that disappeared during reading.
            return FileContent()

        except OSError as exc:
            raise FileContentReadError(
                f"Unable to read repository file {git_file.path!r}: {exc}"
            ) from exc

    def _resolve_file_path(self, relative_path: str) -> Path:
        """Resolve a repository-relative path and prevent directory traversal."""
        windows_path = PureWindowsPath(relative_path)
        posix_path = PurePosixPath(relative_path)

        if (
            not relative_path
            or posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or "\\" in relative_path
            or any(part in {".", ".."} for part in relative_path.split("/"))
            or not posix_path.parts
        ):
            raise UnsafeFilePathError(f"Unsafe repository-relative file path: {relative_path!r}")

        candidate = self._root.joinpath(*posix_path.parts)

        try:
            resolved_parent = candidate.parent.resolve(strict=False)
        except OSError as exc:
            raise FileContentReadError(
                f"Unable to resolve parent directory of {relative_path!r}: {exc}"
            ) from exc

        if resolved_parent != self._root and self._root not in resolved_parent.parents:
            raise UnsafeFilePathError(f"File path escapes the repository: {relative_path!r}")

        return candidate

    def _decode_content(
        self,
        raw_content: bytes,
        size_bytes: int,
    ) -> FileContent:
        """Detect binary data, truncate oversized files and decode text."""
        truncated = (
            len(raw_content) > self._max_file_size_bytes or size_bytes > self._max_file_size_bytes
        )

        raw_content = raw_content[: self._max_file_size_bytes]

        # Use a sample to identify common binary files.
        binary_sample = raw_content[:8192]

        if b"\0" in binary_sample:
            return FileContent(
                is_binary=True,
                size_bytes=size_bytes,
            )

        return FileContent(
            content=raw_content.decode("utf-8-sig", errors="replace"),
            content_truncated=truncated,
            size_bytes=size_bytes,
        )
