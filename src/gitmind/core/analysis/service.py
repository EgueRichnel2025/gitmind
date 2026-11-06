"""Application service for analyzing selected Git files."""

from pathlib import Path

from gitmind.core.analysis.content import WorkingTreeContentReader
from gitmind.core.analysis.diff import GitDiffReader
from gitmind.core.analysis.models import (
    FileAnalysis,
    FileAnalysisSnapshot,
)
from gitmind.core.selection.models import FileSelectionSnapshot


class FileAnalysisService:
    """Coordinate content and diff readers for selected files."""

    def __init__(
        self,
        repository_root: str | Path,
        max_file_size_bytes: int = 1_000_000,
        max_diff_size_bytes: int = 500_000,
    ) -> None:
        self._content_reader = WorkingTreeContentReader(
            repository_root,
            max_file_size_bytes=max_file_size_bytes,
        )
        self._diff_reader = GitDiffReader(
            repository_root,
            max_diff_size_bytes=max_diff_size_bytes,
        )

    def analyze(
        self,
        selection: FileSelectionSnapshot,
    ) -> FileAnalysisSnapshot:
        """Analyze only selected files, preserving their selection order."""
        if not isinstance(selection, FileSelectionSnapshot):
            raise TypeError("selection must be a FileSelectionSnapshot instance.")

        analyses: list[FileAnalysis] = []

        for selectable_file in selection.selected_files:
            git_file = selectable_file.git_file

            content = self._content_reader.read(git_file)
            diff = self._diff_reader.read(git_file)

            analyses.append(
                FileAnalysis(
                    git_file=git_file,
                    staged_diff=diff.staged_diff,
                    unstaged_diff=diff.unstaged_diff,
                    content=content.content,
                    is_binary=content.is_binary,
                    content_truncated=content.content_truncated,
                    staged_diff_truncated=diff.staged_diff_truncated,
                    unstaged_diff_truncated=diff.unstaged_diff_truncated,
                    size_bytes=content.size_bytes,
                )
            )

        return FileAnalysisSnapshot(files=tuple(analyses))
