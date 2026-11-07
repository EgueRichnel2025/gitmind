"""Data models for Git staging operations."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitStagingResult:
    """Represent the result of staging a selected set of files."""

    selected_paths: tuple[str, ...]
    affected_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.selected_paths, tuple):
            raise TypeError("selected_paths must be a tuple.")

        if not isinstance(self.affected_paths, tuple):
            raise TypeError("affected_paths must be a tuple.")

        if not self.selected_paths:
            raise ValueError("selected_paths cannot be empty.")

        for path in (*self.selected_paths, *self.affected_paths):
            if not isinstance(path, str):
                raise TypeError("All paths must be strings.")

            if not path or "\0" in path:
                raise ValueError("Paths cannot be empty or contain NUL characters.")

        if len(self.selected_paths) != len(set(self.selected_paths)):
            raise ValueError("Duplicate selected paths are not allowed.")

        if len(self.affected_paths) != len(set(self.affected_paths)):
            raise ValueError("Duplicate affected paths are not allowed.")

        if not set(self.selected_paths).issubset(self.affected_paths):
            raise ValueError("All selected paths must be included in affected_paths.")

    @property
    def selected_count(self) -> int:
        """Return the number of selected files."""
        return len(self.selected_paths)

    @property
    def affected_count(self) -> int:
        """Return the number of paths passed to Git."""
        return len(self.affected_paths)
