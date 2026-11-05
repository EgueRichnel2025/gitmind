"""File selection operations for GitMind."""

from gitmind.core.git.status_models import GitStatusSnapshot
from gitmind.core.selection.errors import FileNotFoundInSelectionError
from gitmind.core.selection.models import FileSelectionSnapshot, SelectableFile


class FileSelector:
    """Manage user-selected files without modifying the Git repository."""

    def __init__(self, snapshot: GitStatusSnapshot) -> None:
        if not isinstance(snapshot, GitStatusSnapshot):
            raise TypeError("snapshot must be a GitStatusSnapshot.")

        self._files: dict[str, SelectableFile] = {}

        for git_file in snapshot.files:
            if git_file.path in self._files:
                raise ValueError(f"Duplicate file path in Git status snapshot: {git_file.path}")

            self._files[git_file.path] = SelectableFile(git_file=git_file)

    def _get_file(self, path: str) -> SelectableFile:
        """Return a selectable file or raise an explicit error."""
        if not isinstance(path, str):
            raise TypeError("path must be a string.")

        if not path:
            raise ValueError("path must not be empty.")

        try:
            return self._files[path]
        except KeyError:
            raise FileNotFoundInSelectionError(path) from None

    def _set_selected(self, path: str, selected: bool) -> None:
        """Update the selection state of one file."""
        current = self._get_file(path)

        if current.selected != selected:
            self._files[path] = SelectableFile(
                git_file=current.git_file,
                selected=selected,
            )

    def select(self, path: str) -> FileSelectionSnapshot:
        """Select one file."""
        self._set_selected(path, True)
        return self.get_selection()

    def deselect(self, path: str) -> FileSelectionSnapshot:
        """Deselect one file."""
        self._set_selected(path, False)
        return self.get_selection()

    def toggle(self, path: str) -> FileSelectionSnapshot:
        """Invert the selection state of one file."""
        current = self._get_file(path)

        self._files[path] = SelectableFile(
            git_file=current.git_file,
            selected=not current.selected,
        )

        return self.get_selection()

    def select_all(self) -> FileSelectionSnapshot:
        """Select every available file."""
        for path in self._files:
            self._set_selected(path, True)

        return self.get_selection()

    def deselect_all(self) -> FileSelectionSnapshot:
        """Deselect every available file."""
        for path in self._files:
            self._set_selected(path, False)

        return self.get_selection()

    def get_selection(self) -> FileSelectionSnapshot:
        """Return an immutable snapshot of the current selection."""
        return FileSelectionSnapshot(files=tuple(self._files.values()))
