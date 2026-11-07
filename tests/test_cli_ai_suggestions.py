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
    monkeypatch.setattr(
        cli_module.CommitConfirmationTerminalUI,
        "run",
        lambda self: False,
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


def run_git(path: Path, *args: str) -> str:
    """Execute Git in a temporary repository."""
    result = subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def initialize_committable_repository(path: Path) -> None:
    """Initialize a repository with a committed README file."""
    initialize_repository(path)

    run_git(path, "config", "user.name", "GitMind CLI Tests")
    run_git(path, "config", "user.email", "gitmind-cli@example.com")

    (path / "README.md").write_text(
        "# Initial documentation\\n",
        encoding="utf-8",
    )

    run_git(path, "add", "README.md")
    run_git(path, "commit", "--quiet", "-m", "initial commit")

    (path / "README.md").write_text(
        "# Updated documentation\\n",
        encoding="utf-8",
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


def test_cli_creates_commit_after_explicit_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_committable_repository(tmp_path)

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        select_first_file,
    )

    class FakeProvider:
        def __init__(self, config) -> None:
            pass

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            return json.dumps({"suggestions": SUGGESTIONS})

    class FakeSuggestionUI:
        def __init__(self, suggestions, console) -> None:
            self.suggestions = suggestions

        def run(self) -> str:
            return self.suggestions.messages[0]

    configure_fake_ai(monkeypatch, FakeProvider)

    monkeypatch.setattr(
        cli_module,
        "CommitSuggestionTerminalUI",
        FakeSuggestionUI,
    )

    monkeypatch.setattr(
        cli_module.CommitConfirmationTerminalUI,
        "run",
        lambda self: True,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "Commit Completed" in result.output
    assert SUGGESTIONS[0] in result.output

    assert (
        run_git(
            tmp_path,
            "log",
            "-1",
            "--pretty=%s",
        ).strip()
        == SUGGESTIONS[0]
    )

    assert (
        run_git(
            tmp_path,
            "show",
            "HEAD:README.md",
        )
        == "# Updated documentation\\n"
    )

    assert get_git_status(tmp_path) == ""


def test_cli_declining_commit_preserves_staged_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_committable_repository(tmp_path)

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        SelectionTerminalUI,
        "run",
        select_first_file,
    )

    class FakeProvider:
        def __init__(self, config) -> None:
            pass

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            return json.dumps({"suggestions": SUGGESTIONS})

    class FakeSuggestionUI:
        def __init__(self, suggestions, console) -> None:
            self.suggestions = suggestions

        def run(self) -> str:
            return self.suggestions.messages[0]

    class UnexpectedCommitService:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError(
                "GitCommitService must not be called after declining confirmation."
            )

    configure_fake_ai(monkeypatch, FakeProvider)

    monkeypatch.setattr(
        cli_module,
        "CommitSuggestionTerminalUI",
        FakeSuggestionUI,
    )

    monkeypatch.setattr(
        cli_module.CommitConfirmationTerminalUI,
        "run",
        lambda self: False,
    )

    monkeypatch.setattr(
        cli_module,
        "GitCommitService",
        UnexpectedCommitService,
    )

    previous_commit = run_git(tmp_path, "rev-parse", "HEAD").strip()

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "Commit declined" in result.output

    assert run_git(tmp_path, "rev-parse", "HEAD").strip() == previous_commit

    assert run_git(
        tmp_path,
        "diff",
        "--cached",
        "--name-only",
    ).splitlines() == ["README.md"]

    assert (
        run_git(
            tmp_path,
            "show",
            ":README.md",
        )
        == "# Updated documentation\\n"
    )


def create_bare_remote(repository: Path) -> tuple[Path, str, str]:
    """Create a local bare remote and publish the initial branch."""
    branch = run_git(repository, "branch", "--show-current").strip()
    remote = repository.parent / f"{repository.name}-origin.git"

    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(remote)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    run_git(repository, "remote", "add", "origin", str(remote))

    run_git(
        repository,
        "push",
        "--quiet",
        "origin",
        f"HEAD:refs/heads/{branch}",
    )

    initial_commit = subprocess.run(
        [
            "git",
            "--git-dir",
            str(remote),
            "rev-parse",
            f"refs/heads/{branch}",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    return remote, branch, initial_commit


def get_remote_commit(remote: Path, branch: str) -> str:
    """Return the commit stored in a branch of a bare remote."""
    result = subprocess.run(
        [
            "git",
            "--git-dir",
            str(remote),
            "rev-parse",
            f"refs/heads/{branch}",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def test_cli_pushes_commit_after_explicit_push_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_committable_repository(tmp_path)
    remote, branch, initial_commit = create_bare_remote(tmp_path)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(SelectionTerminalUI, "run", select_first_file)

    class FakeProvider:
        def __init__(self, config) -> None:
            pass

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            return json.dumps({"suggestions": SUGGESTIONS})

    class FakeSuggestionUI:
        def __init__(self, suggestions, console) -> None:
            self.suggestions = suggestions

        def run(self) -> str:
            return self.suggestions.messages[0]

    configure_fake_ai(monkeypatch, FakeProvider)

    monkeypatch.setattr(
        cli_module,
        "CommitSuggestionTerminalUI",
        FakeSuggestionUI,
    )
    monkeypatch.setattr(
        cli_module.CommitConfirmationTerminalUI,
        "run",
        lambda self: True,
    )
    monkeypatch.setattr(
        cli_module.PushConfirmationTerminalUI,
        "run",
        lambda self: True,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "Commit Completed" in result.output
    assert "Push Completed" in result.output

    local_commit = run_git(tmp_path, "rev-parse", "HEAD").strip()

    assert local_commit != initial_commit
    assert get_remote_commit(remote, branch) == local_commit
    assert get_git_status(tmp_path) == ""


def test_cli_declining_push_keeps_commit_local(
    tmp_path: Path,
    monkeypatch,
) -> None:
    initialize_committable_repository(tmp_path)
    remote, branch, initial_commit = create_bare_remote(tmp_path)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(SelectionTerminalUI, "run", select_first_file)

    class FakeProvider:
        def __init__(self, config) -> None:
            pass

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            return json.dumps({"suggestions": SUGGESTIONS})

    class FakeSuggestionUI:
        def __init__(self, suggestions, console) -> None:
            self.suggestions = suggestions

        def run(self) -> str:
            return self.suggestions.messages[0]

    configure_fake_ai(monkeypatch, FakeProvider)

    monkeypatch.setattr(
        cli_module,
        "CommitSuggestionTerminalUI",
        FakeSuggestionUI,
    )
    monkeypatch.setattr(
        cli_module.CommitConfirmationTerminalUI,
        "run",
        lambda self: True,
    )
    monkeypatch.setattr(
        cli_module.PushConfirmationTerminalUI,
        "run",
        lambda self: False,
    )

    result = runner.invoke(cli_module.app)

    assert result.exit_code == 0, result.output
    assert "Commit Completed" in result.output
    assert "Push declined" in result.output

    local_commit = run_git(tmp_path, "rev-parse", "HEAD").strip()

    assert local_commit != initial_commit
    assert get_remote_commit(remote, branch) == initial_commit
    assert get_git_status(tmp_path) == ""
