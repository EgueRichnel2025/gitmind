"""Integration tests for the Git staging service."""

import subprocess
from pathlib import Path

import pytest

from gitmind.core.git.errors import GitRunnerError
from gitmind.core.git.runner import GitRunner
from gitmind.core.git.staging import GitStagingService
from gitmind.core.git.staging_errors import (
    EmptyGitStagingSelectionError,
    UnsafeGitPathError,
)
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


def test_staging_service_stages_only_selected_files(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "app.py": "initial app\n",
            "README.md": "initial documentation\n",
            "tests.py": "initial tests\n",
        },
    )

    (tmp_path / "app.py").write_text("updated app\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("updated documentation\n", encoding="utf-8")
    (tmp_path / "tests.py").write_text("updated tests\n", encoding="utf-8")

    selection = build_selection(tmp_path, {"app.py"})

    result = GitStagingService(tmp_path).stage(selection)

    assert result.selected_paths == ("app.py",)
    assert result.affected_paths == ("app.py",)
    assert result.selected_count == 1

    assert get_cached_paths(tmp_path) == {"app.py"}
    assert get_unstaged_paths(tmp_path) == {"README.md", "tests.py"}


def test_staging_preserves_preexisting_staged_changes(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "already_staged.py": "initial content\n",
            "selected.py": "initial content\n",
        },
    )

    staged_file = tmp_path / "already_staged.py"

    staged_file.write_text("content already staged\n", encoding="utf-8")
    run_git(tmp_path, "add", "--", "already_staged.py")

    staged_file.write_text("additional unstaged content\n", encoding="utf-8")

    (tmp_path / "selected.py").write_text(
        "selected modification\n",
        encoding="utf-8",
    )

    selection = build_selection(tmp_path, {"selected.py"})

    GitStagingService(tmp_path).stage(selection)

    assert get_cached_paths(tmp_path) == {
        "already_staged.py",
        "selected.py",
    }

    assert get_unstaged_paths(tmp_path) == {"already_staged.py"}

    staged_content = run_git(
        tmp_path,
        "show",
        ":already_staged.py",
    )

    assert staged_content == "content already staged\n"


def test_staging_adds_selected_untracked_files(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "initial documentation\n",
        },
    )

    new_file = tmp_path / "new feature.py"
    new_file.write_text("print('new feature')\n", encoding="utf-8")

    selection = build_selection(tmp_path, {"new feature.py"})

    result = GitStagingService(tmp_path).stage(selection)

    assert result.selected_paths == ("new feature.py",)
    assert get_cached_paths(tmp_path) == {"new feature.py"}

    tracked = run_git(tmp_path, "ls-files", "--", "new feature.py")
    assert tracked.strip() == "new feature.py"


def test_staging_handles_special_file_names(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "initial documentation\n",
        },
    )

    special_files = [
        "-leading.py",
        "feature[1].py",
        "feature1.py",
    ]

    for name in special_files:
        (tmp_path / name).write_text(
            f"print({name!r})\n",
            encoding="utf-8",
        )

    selection = build_selection(
        tmp_path,
        {"-leading.py", "feature[1].py"},
    )

    GitStagingService(tmp_path).stage(selection)

    assert get_cached_paths(tmp_path) == {
        "-leading.py",
        "feature[1].py",
    }


def test_staging_stages_selected_deletions(
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

    selection = build_selection(tmp_path, {"obsolete.py"})

    GitStagingService(tmp_path).stage(selection)

    staged_changes = run_git(
        tmp_path,
        "diff",
        "--cached",
        "--name-status",
    )

    assert staged_changes.splitlines() == ["D\tobsolete.py"]


def test_staging_rejects_empty_selection(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "documentation\n",
        },
    )

    selection = FileSelectionSnapshot(files=())

    service = GitStagingService(tmp_path)

    with pytest.raises(EmptyGitStagingSelectionError):
        service.stage(selection)


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
def test_staging_rejects_unsafe_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "documentation\n",
        },
    )

    git_file = GitFileStatus(
        path=unsafe_path,
        index_status="?",
        worktree_status="?",
    )

    selection = FileSelectionSnapshot(
        files=(
            SelectableFile(
                git_file=git_file,
                selected=True,
            ),
        )
    )

    service = GitStagingService(tmp_path)

    with pytest.raises(UnsafeGitPathError):
        service.stage(selection)

    assert get_cached_paths(tmp_path) == set()


def test_staging_rejects_invalid_selection_type(
    tmp_path: Path,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "README.md": "documentation\n",
        },
    )

    service = GitStagingService(tmp_path)

    with pytest.raises(TypeError, match="FileSelectionSnapshot"):
        service.stage(None)  # type: ignore[arg-type]


def test_staging_propagates_git_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialize_repository(
        tmp_path,
        {
            "app.py": "initial content\n",
        },
    )

    (tmp_path / "app.py").write_text("modified content\n", encoding="utf-8")

    selection = build_selection(tmp_path, {"app.py"})

    service = GitStagingService(tmp_path)

    def fail_git_command(*args, **kwargs):
        from gitmind.core.git.errors import GitNotFoundError

        raise GitNotFoundError("simulated-git")

    monkeypatch.setattr(
        service._runner,
        "run",
        fail_git_command,
    )

    with pytest.raises(GitRunnerError):
        service.stage(selection)
