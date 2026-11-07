"""Integration tests for the Git push service."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.git.push import GitPushService
from gitmind.core.git.push_errors import (
    GitPushDetachedHeadError,
    GitPushRemoteNotFoundError,
)


def run_git(path: Path, *args: str) -> str:
    """Execute Git in a temporary repository."""
    result = subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def initialize_repository(path: Path) -> None:
    """Initialize a repository with an initial commit."""
    run_git(path, "init", "--quiet")
    run_git(path, "config", "user.name", "GitMind Push Tests")
    run_git(path, "config", "user.email", "gitmind-push@example.com")

    (path / "README.md").write_text(
        "# Initial documentation\n",
        encoding="utf-8",
    )

    run_git(path, "add", "README.md")
    run_git(path, "commit", "--quiet", "-m", "initial commit")
    run_git(path, "branch", "-M", "main")


def create_bare_remote(path: Path) -> Path:
    """Create a local bare remote repository."""
    remote = path / "remote.git"

    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )

    return remote


def prepare_feature_branch(
    repository: Path,
    remote: Path,
) -> str:
    """Create a feature branch with an intentionally incorrect upstream."""
    run_git(repository, "remote", "add", "origin", str(remote))

    run_git(
        repository,
        "push",
        "--quiet",
        "--set-upstream",
        "origin",
        "main",
    )

    branch = "phase/ai-commit-suggestions"

    run_git(repository, "switch", "-c", branch)

    (repository / "feature.py").write_text(
        "print('GitMind')\n",
        encoding="utf-8",
    )

    run_git(repository, "add", "feature.py")
    run_git(
        repository,
        "commit",
        "--quiet",
        "-m",
        "feat: add feature",
    )

    # Simulate the incorrect tracking configuration currently present
    # in the development worktree.
    run_git(
        repository,
        "branch",
        "--set-upstream-to=origin/main",
        branch,
    )

    return branch


def get_remote_commit(
    remote: Path,
    branch: str,
) -> str | None:
    """Return the commit stored in a remote branch."""
    result = subprocess.run(
        [
            "git",
            "--git-dir",
            str(remote),
            "rev-parse",
            f"refs/heads/{branch}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def test_push_targets_current_branch_without_updating_main(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    remote = create_bare_remote(tmp_path)
    branch = prepare_feature_branch(tmp_path, remote)

    original_main_commit = get_remote_commit(remote, "main")

    result = GitPushService(tmp_path).push()

    local_commit = run_git(tmp_path, "rev-parse", "HEAD").strip()

    assert result.remote_name == "origin"
    assert result.branch == branch
    assert result.upstream == f"origin/{branch}"
    assert result.commit_hash == local_commit

    assert get_remote_commit(remote, branch) == local_commit

    # The existing main branch must remain untouched.
    assert get_remote_commit(remote, "main") == original_main_commit

    # The incorrect upstream must be corrected after a successful push.
    upstream = run_git(
        tmp_path,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    ).strip()

    assert upstream == f"origin/{branch}"


def test_push_rejects_missing_remote(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    service = GitPushService(tmp_path)

    with pytest.raises(GitPushRemoteNotFoundError) as exc_info:
        service.push()

    assert exc_info.value.remote_name == "origin"


def test_push_rejects_detached_head(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    run_git(tmp_path, "checkout", "--detach", "HEAD")

    service = GitPushService(tmp_path)

    with pytest.raises(GitPushDetachedHeadError):
        service.push()


def test_push_rejects_invalid_remote_name(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    with pytest.raises(ValueError, match="Invalid Git remote name"):
        GitPushService(
            repository_root=tmp_path,
            remote_name="-unsafe",
        )


def test_push_result_contains_expected_information(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    remote = create_bare_remote(tmp_path)
    branch = prepare_feature_branch(tmp_path, remote)

    result = GitPushService(tmp_path).push()

    assert result.remote_name == "origin"
    assert result.branch == branch
    assert len(result.commit_hash) in {40, 64}
