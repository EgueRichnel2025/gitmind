"""Tests for safe working-tree file content reading."""

from pathlib import Path

import pytest

from gitmind.core.analysis.content import (
    FileContent,
    FileContentReadError,
    UnsafeFilePathError,
    WorkingTreeContentReader,
)
from gitmind.core.git.status_models import GitFileStatus


def make_git_file(
    path: str,
    index_status: str = " ",
    worktree_status: str = "M",
) -> GitFileStatus:
    return GitFileStatus(
        path=path,
        index_status=index_status,
        worktree_status=worktree_status,
    )


def test_reader_reads_utf8_text_file(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "main.py"
    file_path.parent.mkdir()
    file_path.write_bytes(b"print('GitMind')\n")

    reader = WorkingTreeContentReader(tmp_path)

    result = reader.read(make_git_file("src/main.py"))

    assert result.content == "print('GitMind')\n"
    assert result.is_binary is False
    assert result.content_truncated is False
    assert result.size_bytes == file_path.stat().st_size


def test_reader_preserves_empty_files(tmp_path: Path) -> None:
    (tmp_path / "empty.py").write_bytes(b"")

    reader = WorkingTreeContentReader(tmp_path)

    result = reader.read(make_git_file("empty.py"))

    assert result.content == ""
    assert result.is_binary is False
    assert result.content_truncated is False
    assert result.size_bytes == 0


def test_reader_detects_binary_files(tmp_path: Path) -> None:
    (tmp_path / "image.bin").write_bytes(b"\x89PNG\x00\x01\x02")

    reader = WorkingTreeContentReader(tmp_path)

    result = reader.read(make_git_file("image.bin"))

    assert result.content is None
    assert result.is_binary is True
    assert result.content_truncated is False
    assert result.size_bytes == 7


def test_reader_truncates_large_files(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_bytes(b"abcdefghijkl")

    reader = WorkingTreeContentReader(
        tmp_path,
        max_file_size_bytes=8,
    )

    result = reader.read(make_git_file("large.txt"))

    assert result.content == "abcdefgh"
    assert result.content_truncated is True
    assert result.is_binary is False
    assert result.size_bytes == 12


def test_reader_handles_deleted_files(tmp_path: Path) -> None:
    reader = WorkingTreeContentReader(tmp_path)

    result = reader.read(
        make_git_file(
            "deleted.py",
            worktree_status="D",
        )
    )

    assert result == FileContent()


def test_reader_does_not_read_directories(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()

    reader = WorkingTreeContentReader(tmp_path)

    result = reader.read(make_git_file("folder"))

    assert result == FileContent()


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.txt",
        "src/../../outside.txt",
        "/etc/passwd",
        "C:/Windows/system.ini",
        "C:Windows/system.ini",
        r"src\..\outside.txt",
    ],
)
def test_reader_rejects_unsafe_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    reader = WorkingTreeContentReader(tmp_path)

    with pytest.raises(UnsafeFilePathError):
        reader.read(make_git_file(unsafe_path))


def test_reader_rejects_paths_through_external_parent_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    external = tmp_path / "external"
    repository.mkdir()
    external.mkdir()

    link = repository / "external-link"

    try:
        link.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symbolic links are unavailable.")

    (external / "secret.txt").write_text("private", encoding="utf-8")

    reader = WorkingTreeContentReader(repository)

    with pytest.raises(UnsafeFilePathError):
        reader.read(make_git_file("external-link/secret.txt"))


def test_reader_requires_git_file_status(tmp_path: Path) -> None:
    reader = WorkingTreeContentReader(tmp_path)

    with pytest.raises(TypeError):
        reader.read("main.py")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, True, 1.5, "100"],
)
def test_reader_rejects_invalid_file_size_limit(
    tmp_path: Path,
    invalid_limit: object,
) -> None:
    with pytest.raises(ValueError):
        WorkingTreeContentReader(
            tmp_path,
            max_file_size_bytes=invalid_limit,  # type: ignore[arg-type]
        )


def test_reader_requires_existing_repository_directory(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        WorkingTreeContentReader(missing)


def test_reader_requires_directory_as_repository_root(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        WorkingTreeContentReader(file_path)


def test_reader_wraps_os_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "restricted.py"
    file_path.write_bytes(b"private content")

    reader = WorkingTreeContentReader(tmp_path)

    def fail_open(
        path: Path,
        *args: object,
        **kwargs: object,
    ) -> object:
        raise PermissionError("access denied")

    monkeypatch.setattr(Path, "open", fail_open)

    with pytest.raises(FileContentReadError, match="restricted.py"):
        reader.read(make_git_file("restricted.py"))


def test_file_content_rejects_binary_text_content() -> None:
    with pytest.raises(ValueError):
        FileContent(
            content="not allowed",
            is_binary=True,
        )


def test_file_content_rejects_truncation_without_content() -> None:
    with pytest.raises(ValueError):
        FileContent(
            content=None,
            content_truncated=True,
        )
