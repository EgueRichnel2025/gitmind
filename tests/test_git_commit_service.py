"""Integration tests for the Git commit service."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.git.commit import GitCommitService
from gitmind.core.git.commit_errors import (
    EmptyGitCommitSelectionError,
    GitCommitSelectionHasUnstagedChangesError,
    GitCommitSelectionNotStagedError,
    GitCommitSelectionUnmergedError,
    InvalidGitCommitMessageError,
    UnsafeGitCommitPathError,
)
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.staging import GitStagingService
from gitmind.core.git.status_models import GitFileStatus
from gitmind.core.git.status_service import GitStatusService
from gitmind.core.selection.models import (
    FileSelectionSnapshot,
    SelectableFile,
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


def initialize_repository(
    path: Path,
    files: dict[str, str],
) -> None:
    """Create a repository with an initial commit."""
    run_git(path, "init", "--quiet")
    run_git(path, "config", "user.name", "GitMind Tests")
    run_git(path, "config", "user.email", "gitmind-tests@example.com")

    for relative_path, content in files.items():
        file_path = path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    run_git(path, "add", "--all")
    run_git(path, "commit", "--quiet", "-m", "initial commit")


def build_selection(
    repository: Path,
    selected_paths: set[str],
) -> FileSelectionSnapshot:
    """Build a selection from the current repository status."""
    snapshot = GitStatusService(
        runner=GitRunner(),
    ).get_status(repository)

    available_paths = {file.path for file in snapshot.files}

    if not selected_paths.issubset(available_paths):
        raise AssertionError("Selected paths must exist in the Git status snapshot.")

    return FileSelectionSnapshot(
        files=tuple(
            SelectableFile(
                git_file=git_file,
                selected=git_file.path in selected_paths,
            )
            for git_file in snapshot.files
        )
    )


def get_cached_paths(repository: Path) -> set[str]:
    """Return paths currently staged in the Git index."""
    output = run_git(
        repository,
        "diff",
        "--cached",
        "--name-only",
    )
    return set(output.splitlines())


def get_unstaged_paths(repository: Path) -> set[str]:
    """Return tracked paths with unstaged modifications."""
    output = run_git(
        repository,
        "diff",
        "--name-only",
    )
    return set(output.splitlines())


def get_head_paths(repository: Path) -> set[str]:
    """Return tracked paths in the current commit."""
    output = run_git(
        repository,
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
    )
    return set(output.splitlines())


def get_last_commit_paths(repository: Path) -> set[str]:
    """Return paths changed by the latest commit."""
    output = run_git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        "HEAD",
    )
    return set(output.splitlines())


def test_commit_only_selected_files_and_preserves_other_staged_changes(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "selected.py": "initial selected content\n",
            "already_staged.py": "initial staged content\n",
            "README.md": "initial documentation\n",
        },
    )

    (tmp_path / "selected.py").write_text(
        "updated selected content\n",
        encoding="utf-8",
    )
    (tmp_path / "already_staged.py").write_text(
        "updated staged content\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "updated documentation\n",
        encoding="utf-8",
    )

    run_git(
        tmp_path,
        "add",
        "--",
        "selected.py",
        "already_staged.py",
    )

    selection = build_selection(tmp_path, {"selected.py"})

    result = GitCommitService(tmp_path).commit(
        selection,
        "feat: update selected file",
    )

    assert result.message == "feat: update selected file"
    assert result.committed_paths == ("selected.py",)
    assert result.committed_count == 1
    assert len(result.commit_hash) in {40, 64}

    assert get_last_commit_paths(tmp_path) == {"selected.py"}

    assert (
        run_git(
            tmp_path,
            "show",
            "HEAD:selected.py",
        )
        == "updated selected content\n"
    )

    assert (
        run_git(
            tmp_path,
            "show",
            "HEAD:already_staged.py",
        )
        == "initial staged content\n"
    )

    assert (
        run_git(
            tmp_path,
            "show",
            ":already_staged.py",
        )
        == "updated staged content\n"
    )

    assert get_cached_paths(tmp_path) == {"already_staged.py"}
    assert get_unstaged_paths(tmp_path) == {"README.md"}


def test_commit_selected_new_file_after_staging(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "initial documentation\n",
        },
    )

    new_file = tmp_path / "new_feature.py"
    new_file.write_text(
        "print('new feature')\n",
        encoding="utf-8",
    )

    selection = build_selection(tmp_path, {"new_feature.py"})

    GitStagingService(tmp_path).stage(selection)

    result = GitCommitService(tmp_path).commit(
        selection,
        "feat: add new feature",
    )

    assert result.committed_paths == ("new_feature.py",)
    assert get_last_commit_paths(tmp_path) == {"new_feature.py"}
    assert get_cached_paths(tmp_path) == set()
    assert "new_feature.py" in get_head_paths(tmp_path)


def test_commit_selected_deletion(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "obsolete.py": "obsolete content\n",
            "keep.py": "keep content\n",
        },
    )

    (tmp_path / "obsolete.py").unlink()

    run_git(
        tmp_path,
        "add",
        "-u",
        "--",
        "obsolete.py",
    )

    selection = build_selection(tmp_path, {"obsolete.py"})

    result = GitCommitService(tmp_path).commit(
        selection,
        "refactor: remove obsolete file",
    )

    assert result.committed_paths == ("obsolete.py",)
    assert "obsolete.py" not in get_head_paths(tmp_path)
    assert get_last_commit_paths(tmp_path) == {"obsolete.py"}


def test_commit_handles_special_file_names(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "initial documentation\n",
        },
    )

    special_files = {
        "-leading.py": "print('leading')\n",
        "feature[1].py": "print('feature 1')\n",
        "feature1.py": "print('feature one')\n",
    }

    for name, content in special_files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")

    selected_paths = {"-leading.py", "feature[1].py"}

    selection = build_selection(tmp_path, selected_paths)

    GitStagingService(tmp_path).stage(selection)

    result = GitCommitService(tmp_path).commit(
        selection,
        "feat: add selected special files",
    )

    assert set(result.committed_paths) == selected_paths
    assert get_last_commit_paths(tmp_path) == selected_paths
    assert "feature1.py" not in get_last_commit_paths(tmp_path)
    assert get_cached_paths(tmp_path) == set()


def test_commit_handles_staged_rename(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "old_name.py": "original content\n",
        },
    )

    run_git(
        tmp_path,
        "mv",
        "old_name.py",
        "new_name.py",
    )

    selection = build_selection(tmp_path, {"new_name.py"})

    result = GitCommitService(tmp_path).commit(
        selection,
        "refactor: rename file",
    )

    assert result.committed_paths == ("new_name.py",)
    assert get_head_paths(tmp_path) == {"new_name.py"}
    assert (tmp_path / "new_name.py").read_text(encoding="utf-8") == ("original content\n")
    assert get_cached_paths(tmp_path) == set()


def test_commit_rejects_empty_selection(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "documentation\n",
        },
    )

    selection = FileSelectionSnapshot(files=())

    with pytest.raises(EmptyGitCommitSelectionError):
        GitCommitService(tmp_path).commit(
            selection,
            "feat: empty commit",
        )


def test_commit_rejects_file_that_is_not_staged(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "selected.py": "initial content\n",
        },
    )

    (tmp_path / "selected.py").write_text(
        "unstaged modification\n",
        encoding="utf-8",
    )

    selection = build_selection(tmp_path, {"selected.py"})

    with pytest.raises(GitCommitSelectionNotStagedError) as exc_info:
        GitCommitService(tmp_path).commit(
            selection,
            "feat: update selected file",
        )

    assert exc_info.value.path == "selected.py"
    assert get_cached_paths(tmp_path) == set()


def test_commit_rejects_selected_file_with_unstaged_changes(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "selected.py": "initial content\n",
        },
    )

    selected_file = tmp_path / "selected.py"

    selected_file.write_text(
        "staged content\n",
        encoding="utf-8",
    )

    run_git(tmp_path, "add", "--", "selected.py")

    selected_file.write_text(
        "additional unstaged content\n",
        encoding="utf-8",
    )

    selection = build_selection(tmp_path, {"selected.py"})

    with pytest.raises(
        GitCommitSelectionHasUnstagedChangesError,
    ) as exc_info:
        GitCommitService(tmp_path).commit(
            selection,
            "feat: update selected file",
        )

    assert exc_info.value.path == "selected.py"
    assert get_cached_paths(tmp_path) == {"selected.py"}
    assert get_unstaged_paths(tmp_path) == {"selected.py"}


def test_commit_rejects_file_that_was_unstaged_after_selection(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "selected.py": "initial content\n",
        },
    )

    (tmp_path / "selected.py").write_text(
        "staged content\n",
        encoding="utf-8",
    )

    run_git(tmp_path, "add", "--", "selected.py")

    selection = build_selection(tmp_path, {"selected.py"})

    run_git(
        tmp_path,
        "reset",
        "--quiet",
        "HEAD",
        "--",
        "selected.py",
    )

    with pytest.raises(GitCommitSelectionNotStagedError):
        GitCommitService(tmp_path).commit(
            selection,
            "feat: update selected file",
        )

    assert get_cached_paths(tmp_path) == set()


@pytest.mark.parametrize(
    "message",
    [
        "",
        "   ",
        "message\nsecond line",
        "message\rsecond line",
        " message",
        "message ",
        "message\0tail",
    ],
)
def test_commit_rejects_invalid_messages(
    tmp_path: Path,
    message: str,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "selected.py": "initial content\n",
        },
    )

    (tmp_path / "selected.py").write_text(
        "updated content\n",
        encoding="utf-8",
    )
    run_git(tmp_path, "add", "--", "selected.py")

    selection = build_selection(tmp_path, {"selected.py"})

    with pytest.raises(InvalidGitCommitMessageError):
        GitCommitService(tmp_path).commit(selection, message)

    assert get_cached_paths(tmp_path) == {"selected.py"}


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.py",
        "src/../../outside.py",
        "/outside.py",
        "C:/outside.py",
        r"C:\outside.py",
        r"src\..\outside.py",
        ".",
    ],
)
def test_commit_rejects_unsafe_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "documentation\n",
        },
    )

    fake_file = GitFileStatus(
        path=unsafe_path,
        index_status="M",
        worktree_status=" ",
    )

    selection = FileSelectionSnapshot(
        files=(
            SelectableFile(
                git_file=fake_file,
                selected=True,
            ),
        )
    )

    with pytest.raises(UnsafeGitCommitPathError):
        GitCommitService(tmp_path).commit(
            selection,
            "feat: test unsafe path",
        )


def test_commit_rejects_unmerged_files(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "conflict.py": "original content\n",
        },
    )

    current_branch = run_git(
        tmp_path,
        "branch",
        "--show-current",
    ).strip()

    run_git(tmp_path, "switch", "-c", "feature")

    (tmp_path / "conflict.py").write_text(
        "feature content\n",
        encoding="utf-8",
    )
    run_git(tmp_path, "add", "--", "conflict.py")
    run_git(tmp_path, "commit", "--quiet", "-m", "feature change")

    run_git(tmp_path, "switch", current_branch)

    (tmp_path / "conflict.py").write_text(
        "main content\n",
        encoding="utf-8",
    )
    run_git(tmp_path, "add", "--", "conflict.py")
    run_git(tmp_path, "commit", "--quiet", "-m", "main change")

    merge_result = subprocess.run(
        ["git", "merge", "feature"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert merge_result.returncode != 0

    selection = build_selection(tmp_path, {"conflict.py"})

    with pytest.raises(GitCommitSelectionUnmergedError):
        GitCommitService(tmp_path).commit(
            selection,
            "feat: commit conflicted file",
        )
