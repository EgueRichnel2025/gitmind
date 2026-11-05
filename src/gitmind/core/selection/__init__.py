"""Public API for GitMind file selection."""

from gitmind.core.selection.errors import (
    FileNotFoundInSelectionError,
    FileSelectionError,
)
from gitmind.core.selection.models import (
    FileSelectionSnapshot,
    SelectableFile,
)
from gitmind.core.selection.pagination import FileSelectionPager
from gitmind.core.selection.pagination_models import FileSelectionPage
from gitmind.core.selection.selector import FileSelector
from gitmind.core.selection.service import FileSelectionService

__all__ = [
    "FileNotFoundInSelectionError",
    "FileSelectionError",
    "FileSelectionPage",
    "FileSelectionPager",
    "FileSelectionService",
    "FileSelectionSnapshot",
    "FileSelector",
    "SelectableFile",
]
