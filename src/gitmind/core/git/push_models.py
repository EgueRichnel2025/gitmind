"""Data models for Git push operations."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitPushResult:
    """Represent a successfully pushed local branch."""

    remote_name: str
    branch: str
    commit_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.remote_name, str) or not self.remote_name.strip():
            raise ValueError("remote_name cannot be empty.")

        if not isinstance(self.branch, str) or not self.branch.strip():
            raise ValueError("branch cannot be empty.")

        if not isinstance(self.commit_hash, str):
            raise TypeError("commit_hash must be a string.")

        if len(self.commit_hash) not in {40, 64}:
            raise ValueError("commit_hash must contain 40 or 64 characters.")

        if any(character not in "0123456789abcdefABCDEF" for character in self.commit_hash):
            raise ValueError("commit_hash must be hexadecimal.")

    @property
    def upstream(self) -> str:
        """Return the configured upstream reference."""
        return f"{self.remote_name}/{self.branch}"
