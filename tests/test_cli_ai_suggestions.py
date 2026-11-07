"""Integration tests for AI commit suggestions in the CLI."""

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import gitmind.cli as cli_module
from gitmind.core.ai import (
    AIAuthenticationError,
    AIConfigurationError,
    AIProviderConfig,
)
from gitmind.ui.selection import SelectionTerminalUI

runner = CliRunner()


@pytest.fixture(autouse=True)
def confirm_staging_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Confirm staging without opening an interactive prompt."""
    monkeypatch.setattr(
        cli_module.StagingConfirmationTerminalUI,
        "run",
        lambda self: True,
    )


SUGGESTIONS = [
    "docs: add project documentation",
    "docs: improve installation instructions",
    "docs: describe GitMind workflow",
]


def initialize_repository(path: Path) -> None:
    """Initialize a temporary Git repository."""
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def get_git_status(path: Path) -> str:
    """Return the repository's porcelain Git status."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def select_first_file(ui: SelectionTerminalUI):
    """Simulate confirmation with the first file selected."""
    snapshot = ui._service.get_selection()

    if snapshot.files:
        ui._service.select(snapshot.files[0].path)

    return ui._service.get_selection()


def configure_fake_ai(monkeypatch, provider_class) -> None:
    """Configure a fake API provider without using a real API key."""
    config = AIProviderConfig(
        api_key="test-api-key",
        model="test-model",
    )

    monkeypatch.setattr(
        cli_module.AIProviderConfig,
        "from_env",
        classmethod(lambda cls: config),
    )

    monkeypatch.setattr(
        cli_module,
        "OpenAICompatibleProvider",
        provider_class,
    )


def test_cli_generates_and_displays_three_commit_suggestions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_text(
        "# Demo\n\nGitMind project documentation.\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        select_first_file,
    )

    captured = {}

    class FakeProvider:
        def __init__(self, config) -> None:
            captured["model"] = config.model

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            captured["system_prompt"] = system_prompt
            captured["user_prompt"] = user_prompt

            return json.dumps(
                {
                    "suggestions": SUGGESTIONS,
                }
            )

    class FakeSuggestionUI:
        def __init__(self, suggestions, console) -> None:
            captured["suggestions"] = suggestions

        def run(self) -> str:
            return captured["suggestions"].messages[1]

    configure_fake_ai(monkeypatch, FakeProvider)

    monkeypatch.setattr(
        cli_module,
        "CommitSuggestionTerminalUI",
        FakeSuggestionUI,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "Analysis completed" in result.output
    assert "Three commit message suggestions generated successfully" in result.output
    assert "Selected Commit Message" in result.output
    assert SUGGESTIONS[1] in result.output

    assert captured["model"] == "test-model"
    assert len(captured["suggestions"].messages) == 3
    assert "README.md" in captured["user_prompt"]
    assert "GitMind project documentation" in captured["user_prompt"]

    # The selected suggestion must never stage or commit the file.
    assert "A  README.md" in get_git_status(tmp_path)


def test_cli_handles_missing_ai_configuration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_text(
        "# Demo\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        select_first_file,
    )

    def missing_configuration(cls):
        raise AIConfigurationError("GITMIND_AI_API_KEY is not configured.")

    monkeypatch.setattr(
        cli_module.AIProviderConfig,
        "from_env",
        classmethod(missing_configuration),
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "AI Configuration" in result.output
    assert "GITMIND_AI_API_KEY" in result.output
    assert "Selected files remain staged" in result.output
    assert "A  README.md" in get_git_status(tmp_path)


def test_cli_handles_ai_provider_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "README.md").write_text(
        "# Demo\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        select_first_file,
    )

    class FailedProvider:
        def __init__(self, config) -> None:
            pass

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            raise AIAuthenticationError("Simulated provider authentication failure.")

    configure_fake_ai(monkeypatch, FailedProvider)

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "GitMind | AI Error" in result.output
    assert "Unable to generate commit suggestions" in result.output
    assert "No commit was created" in result.output

    assert "A  README.md" in get_git_status(tmp_path)
