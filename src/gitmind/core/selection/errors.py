"""Exceptions for GitMind file selection."""


class FileSelectionError(RuntimeError):
    """Base exception for file selection errors."""


class FileNotFoundInSelectionError(FileSelectionError):
    """Raised when a requested file is absent from the selection."""

    def __init__(self, path: str) -> None:
        self.path = path

        super().__init__(f"File '{path}' is not available in the current selection.")
