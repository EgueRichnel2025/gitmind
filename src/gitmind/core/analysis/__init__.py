"""File analysis engine for GitMind."""

from gitmind.core.analysis.content import (
    FileContent,
    FileContentReadError,
    UnsafeFilePathError,
    WorkingTreeContentReader,
)
from gitmind.core.analysis.diff import GitDiffReader
from gitmind.core.analysis.diff_models import FileDiff
from gitmind.core.analysis.models import (
    FileAnalysis,
    FileAnalysisSnapshot,
)
from gitmind.core.analysis.service import FileAnalysisService

__all__ = [
    "FileAnalysis",
    "FileAnalysisService",
    "FileAnalysisSnapshot",
    "FileContent",
    "FileContentReadError",
    "FileDiff",
    "GitDiffReader",
    "UnsafeFilePathError",
    "WorkingTreeContentReader",
]
