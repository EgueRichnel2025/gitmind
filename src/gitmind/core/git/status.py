"""Parser for Git porcelain v1 status output."""

from gitmind.core.git.errors import GitStatusParseError
from gitmind.core.git.status_models import GitFileStatus, GitStatusSnapshot


class GitStatusParser:
    """Parse Git porcelain v1 output into structured status objects."""

    def parse(self, output: str) -> GitStatusSnapshot:
        """Parse NUL-delimited Git status output."""
        if not isinstance(output, str):
            raise TypeError("Git status output must be a string.")

        if not output:
            return GitStatusSnapshot(files=())

        records = output.split("\0")

        # Git porcelain v1 -z normally terminates the output with NUL.
        if records[-1] == "":
            records.pop()

        files: list[GitFileStatus] = []
        index = 0

        while index < len(records):
            record = records[index]

            if not record:
                raise GitStatusParseError(
                    "Unexpected empty status record.",
                    entry=record,
                )

            if len(record) < 3 or record[2] != " ":
                raise GitStatusParseError(
                    "Malformed status record. Expected XY followed by a space.",
                    entry=record,
                )

            index_status = record[0]
            worktree_status = record[1]
            path = record[3:]

            if not path:
                raise GitStatusParseError(
                    "Missing filename in status record.",
                    entry=record,
                )

            original_path = None
            requires_original_path = "R" in (index_status, worktree_status) or "C" in (
                index_status,
                worktree_status,
            )

            if requires_original_path:
                if index + 1 >= len(records):
                    raise GitStatusParseError(
                        "Missing original filename for renamed or copied file.",
                        entry=record,
                    )

                original_path = records[index + 1]

                if not original_path:
                    raise GitStatusParseError(
                        "Empty original filename for renamed or copied file.",
                        entry=record,
                    )

                # Porcelain v1 -z stores the destination before the source.
                index += 1

            try:
                file_status = GitFileStatus(
                    path=path,
                    index_status=index_status,
                    worktree_status=worktree_status,
                    original_path=original_path,
                )
            except ValueError as exc:
                raise GitStatusParseError(
                    reason=str(exc),
                    entry=record,
                ) from exc

            files.append(file_status)
            index += 1

        return GitStatusSnapshot(files=tuple(files))
