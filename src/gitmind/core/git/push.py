"""Service for safely pushing the current Git branch."""

from pathlib import Path

from gitmind.core.git.push_errors import (
    GitPushDetachedHeadError,
    GitPushRemoteNotFoundError,
)
from gitmind.core.git.push_models import GitPushResult
from gitmind.core.git.runner import GitRunner


class GitPushService:
    """Push the current branch to the same branch name on a remote."""

    def __init__(
        self,
        repository_root: str | Path,
        runner: GitRunner | None = None,
        remote_name: str = "origin",
    ) -> None:
        root = Path(repository_root)

        if not root.exists():
            raise FileNotFoundError(f"Repository directory does not exist: {root}")

        if not root.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {root}")

        if not isinstance(remote_name, str):
            raise TypeError("remote_name must be a string.")

        if (
            not remote_name
            or remote_name.startswith("-")
            or any(character.isspace() for character in remote_name)
            or "\0" in remote_name
        ):
            raise ValueError("Invalid Git remote name.")

        self._repository_root = root.resolve()
        self._runner = runner if runner is not None else GitRunner()
        self._remote_name = remote_name

    def get_current_branch(self) -> str:
        """Return the current branch or reject a detached HEAD."""
        result = self._runner.run(
            "branch",
            "--show-current",
            cwd=self._repository_root,
        )

        branch = result.stdout.strip()

        if not branch:
            raise GitPushDetachedHeadError()

        return branch

    def _ensure_remote_exists(self) -> None:
        """Verify that the configured remote exists."""
        result = self._runner.run(
            "remote",
            cwd=self._repository_root,
        )

        remotes = set(result.stdout.splitlines())

        if self._remote_name not in remotes:
            raise GitPushRemoteNotFoundError(self._remote_name)

    def validate_target(self) -> str:
        """Validate the current branch and configured remote before asking confirmation."""
        branch = self.get_current_branch()
        self._ensure_remote_exists()
        return branch

    def push(self) -> GitPushResult:
        """Push HEAD to the same branch name on the configured remote.

        The explicit refspec prevents the local branch's potentially
        incorrect upstream configuration from redirecting the push.
        """
        branch = self.validate_target()

        commit_result = self._runner.run(
            "rev-parse",
            "HEAD",
            cwd=self._repository_root,
        )

        commit_hash = commit_result.stdout.strip()

        self._runner.run(
            "push",
            "--set-upstream",
            self._remote_name,
            f"HEAD:refs/heads/{branch}",
            cwd=self._repository_root,
            timeout_seconds=120.0,
        )

        return GitPushResult(
            remote_name=self._remote_name,
            branch=branch,
            commit_hash=commit_hash,
        )
