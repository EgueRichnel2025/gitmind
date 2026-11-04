"""Git repository discovery and identification."""

from dataclasses import dataclass
from pathlib import Path

from gitmind.core.git.runner import GitRunner


@dataclass(frozen=True, slots=True)
class RepositoryInfo:
    """Represent information about a detected Git repository."""

    root: Path


class RepositoryDetector:
    """Detect Git repositories and resolve their root directories."""

    def __init__(self, runner: GitRunner | None = None) -> None:
        self._runner = runner if runner is not None else GitRunner()

    def discover(self, path: str | Path | None = None) -> RepositoryInfo | None:
        """Discover the Git repository containing the given directory."""
        directory = Path.cwd() if path is None else Path(path)

        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")

        directory = directory.resolve()

        result = self._runner.run(
            "rev-parse",
            "--show-toplevel",
            cwd=directory,
            check=False,
        )

        if not result.succeeded:
            return None

        root_output = result.stdout.strip()

        if not root_output:
            return None

        root = Path(root_output).resolve()

        return RepositoryInfo(root=root)

    def is_repository(self, path: str | Path | None = None) -> bool:
        """Return whether the given directory belongs to a Git repository."""
        return self.discover(path) is not None
