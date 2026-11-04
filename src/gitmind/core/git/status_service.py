"""Service for retrieving structured Git repository status."""

from pathlib import Path

from gitmind.core.git.errors import GitRepositoryNotFoundError
from gitmind.core.git.repository import RepositoryDetector
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.status import GitStatusParser
from gitmind.core.git.status_models import GitStatusSnapshot


class GitStatusService:
    """Retrieve and parse the current status of a Git repository."""

    def __init__(
        self,
        runner: GitRunner | None = None,
        parser: GitStatusParser | None = None,
    ) -> None:
        self._runner = runner if runner is not None else GitRunner()
        self._parser = parser if parser is not None else GitStatusParser()
        self._repository_detector = RepositoryDetector(self._runner)

    def get_status(
        self,
        path: str | Path | None = None,
    ) -> GitStatusSnapshot:
        """Retrieve the status of the repository containing the given directory."""
        directory = Path.cwd() if path is None else Path(path)

        repository = self._repository_detector.discover(directory)

        if repository is None:
            raise GitRepositoryNotFoundError(directory.resolve())

        result = self._runner.run(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=repository.root,
        )

        return self._parser.parse(result.stdout)
