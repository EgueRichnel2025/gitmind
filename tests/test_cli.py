"""Tests for the GitMind command-line interface."""

from typer.testing import CliRunner

from gitmind import __version__
from gitmind.cli import app

runner = CliRunner()


def test_help_displays_application_information() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "GitMind" in result.output
    assert "--help" in result.output


def test_version_displays_current_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"GitMind {__version__}"


def test_short_help_displays_application_information() -> None:
    result = runner.invoke(app, ["-h"])

    assert result.exit_code == 0
    assert "GitMind" in result.output
    assert "-h" in result.output
    assert "--help" in result.output
