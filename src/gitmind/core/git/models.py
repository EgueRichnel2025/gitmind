"""Data models used by the Git integration layer."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitCommandResult:
    """Represent the result of an executed Git command."""

    args: tuple[str, ...]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def succeeded(self) -> bool:
        """Return whether the Git command completed successfully."""
        return self.returncode == 0
