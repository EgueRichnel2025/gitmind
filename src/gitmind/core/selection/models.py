"""Data models for GitMind file selection."""

from dataclasses import dataclass

from gitmind.core.git.status_models import GitFileStatus


@dataclass(frozen=True, slots=True)
class SelectableFile:
    """Represent a Git file that can be selected for a commit."""

    git_file: GitFileStatus
    selected: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.git_file, GitFileStatus):
            raise TypeError("git_file must be a GitFileStatus instance.")

        if not isinstance(self.selected, bool):
            raise TypeError("selected must be a boolean.")

    @property
    def path(self) -> str:
        """Return the repository-relative file path."""
        return self.git_file.path


@dataclass(frozen=True, slots=True)
class FileSelectionSnapshot:
    """Represent an immutable snapshot of the current file selection."""

    files: tuple[SelectableFile, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.files, tuple):
            raise TypeError("files must be a tuple of SelectableFile instances.")

        if any(not isinstance(file, SelectableFile) for file in self.files):
            raise TypeError("All files must be SelectableFile instances.")

        paths = [file.path for file in self.files]

        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate file paths are not allowed in a selection.")

    @property
    def total_count(self) -> int:
        """Return the total number of available files."""
        return len(self.files)

    @property
    def selected_count(self) -> int:
        """Return the number of selected files."""
        return sum(file.selected for file in self.files)

    @property
    def unselected_count(self) -> int:
        """Return the number of unselected files."""
        return self.total_count - self.selected_count

    @property
    def selected_files(self) -> tuple[SelectableFile, ...]:
        """Return all selected files while preserving their original order."""
        return tuple(file for file in self.files if file.selected)

    @property
    def unselected_files(self) -> tuple[SelectableFile, ...]:
        """Return all unselected files while preserving their original order."""
        return tuple(file for file in self.files if not file.selected)

    @property
    def selected_paths(self) -> tuple[str, ...]:
        """Return the paths of selected files."""
        return tuple(file.path for file in self.selected_files)

    @property
    def has_selection(self) -> bool:
        """Return whether at least one file is selected."""
        return self.selected_count > 0

    @property
    def all_selected(self) -> bool:
        """Return whether all available files are selected."""
        return self.total_count > 0 and self.selected_count == self.total_count
