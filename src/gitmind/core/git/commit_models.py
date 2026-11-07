"""Data models for Git commit operations."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitCommitResult:
    """Represent a successfully created Git commit."""

    commit_hash: str
    message: str
    committed_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.commit_hash, str):
            raise TypeError("commit_hash must be a string.")

        if len(self.commit_hash) not in {40, 64}:
            raise ValueError("commit_hash must contain 40 or 64 hexadecimal characters.")

        if any(character not in "0123456789abcdefABCDEF" for character in self.commit_hash):
            raise ValueError("commit_hash must be hexadecimal.")

        if not isinstance(self.message, str):
            raise TypeError("message must be a string.")

        if not self.message.strip() or "\0" in self.message:
            raise ValueError("message cannot be empty or contain NUL characters.")

        if "\n" in self.message or "\r" in self.message:
            raise ValueError("message must be a single line.")

        if self.message != self.message.strip():
            raise ValueError("message must not contain surrounding whitespace.")

        if not isinstance(self.committed_paths, tuple):
            raise TypeError("committed_paths must be a tuple.")

        if not self.committed_paths:
            raise ValueError("committed_paths cannot be empty.")

        for path in self.committed_paths:
            if not isinstance(path, str):
                raise TypeError("All committed paths must be strings.")

            if not path or "\0" in path:
                raise ValueError("Committed paths cannot be empty or contain NUL.")

        if len(self.committed_paths) != len(set(self.committed_paths)):
            raise ValueError("Duplicate committed paths are not allowed.")

    @property
    def committed_count(self) -> int:
        """Return the number of committed paths."""
        return len(self.committed_paths)
