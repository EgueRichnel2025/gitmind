"""Tests for Git porcelain v1 status parsing."""

import pytest

from gitmind.core.git.errors import GitStatusParseError
from gitmind.core.git.status import GitStatusParser


@pytest.fixture
def parser() -> GitStatusParser:
    return GitStatusParser()


def test_parse_empty_output(parser: GitStatusParser) -> None:
    snapshot = parser.parse("")

    assert snapshot.is_clean
    assert snapshot.file_count == 0


def test_parse_staged_unstaged_and_mixed_changes(
    parser: GitStatusParser,
) -> None:
    output = " M src/unstaged.py\0M  src/staged.py\0MM src/both.py\0"

    snapshot = parser.parse(output)

    assert snapshot.file_count == 3

    assert snapshot.files[0].status_code == " M"
    assert snapshot.files[0].is_unstaged

    assert snapshot.files[1].status_code == "M "
    assert snapshot.files[1].is_staged

    assert snapshot.files[2].status_code == "MM"
    assert snapshot.files[2].is_staged
    assert snapshot.files[2].is_unstaged


def test_parse_untracked_and_ignored_files(
    parser: GitStatusParser,
) -> None:
    output = "?? src/new_module.py\0!! build/generated.py\0"

    snapshot = parser.parse(output)

    assert snapshot.file_count == 2
    assert snapshot.files[0].is_untracked
    assert snapshot.files[1].is_ignored


def test_parse_added_and_deleted_files(
    parser: GitStatusParser,
) -> None:
    output = "A  src/new_module.py\0D  src/old_module.py\0"

    snapshot = parser.parse(output)

    assert snapshot.files[0].is_added
    assert snapshot.files[1].is_deleted


def test_parse_preserves_spaces_and_unicode_in_filename(
    parser: GitStatusParser,
) -> None:
    path = "src/gestion des utilisateurs-équipe.py"

    snapshot = parser.parse(f"?? {path}\0")

    assert snapshot.files[0].path == path


def test_parse_preserves_tabs_and_newlines_in_filename(
    parser: GitStatusParser,
) -> None:
    path = "src/name\twith\nspecial_characters.py"

    snapshot = parser.parse(f"?? {path}\0")

    assert snapshot.files[0].path == path


def test_parse_renamed_file_with_destination_before_source(
    parser: GitStatusParser,
) -> None:
    output = "R  src/new_name.py\0src/old_name.py\0"

    snapshot = parser.parse(output)

    file = snapshot.files[0]

    assert file.path == "src/new_name.py"
    assert file.original_path == "src/old_name.py"
    assert file.is_renamed


def test_parse_copied_file(parser: GitStatusParser) -> None:
    output = "C  src/copied.py\0src/original.py\0"

    snapshot = parser.parse(output)

    file = snapshot.files[0]

    assert file.path == "src/copied.py"
    assert file.original_path == "src/original.py"
    assert file.is_copied


def test_parse_output_without_trailing_nul(
    parser: GitStatusParser,
) -> None:
    snapshot = parser.parse(" M src/auth.py")

    assert snapshot.file_count == 1
    assert snapshot.files[0].path == "src/auth.py"


def test_parse_rejects_malformed_status_record(
    parser: GitStatusParser,
) -> None:
    with pytest.raises(GitStatusParseError, match="Malformed status record"):
        parser.parse("Msrc/auth.py\0")


def test_parse_rejects_unknown_status_code(
    parser: GitStatusParser,
) -> None:
    with pytest.raises(GitStatusParseError):
        parser.parse("X  src/auth.py\0")


def test_parse_rejects_renamed_file_without_original_path(
    parser: GitStatusParser,
) -> None:
    with pytest.raises(GitStatusParseError, match="Missing original filename"):
        parser.parse("R  src/new.py\0")


def test_parse_rejects_empty_original_path(
    parser: GitStatusParser,
) -> None:
    with pytest.raises(GitStatusParseError, match="Empty original filename"):
        parser.parse("R  src/new.py\0\0")


def test_parse_rejects_unexpected_empty_record(
    parser: GitStatusParser,
) -> None:
    output = " M src/first.py\0\0 M src/second.py\0"

    with pytest.raises(GitStatusParseError, match="Unexpected empty"):
        parser.parse(output)


def test_parse_rejects_missing_filename(
    parser: GitStatusParser,
) -> None:
    with pytest.raises(GitStatusParseError, match="Missing filename"):
        parser.parse(" M \0")
