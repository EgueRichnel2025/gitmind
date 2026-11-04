# GitMind

An AI-powered Git workflow assistant for developers.

GitMind aims to simplify the daily Git workflow by helping developers review modified files, select changes, generate meaningful commit messages, create commits and optionally push them to a remote repository.

## Project Status

GitMind is currently under active development.

The initial foundation provides:

- Python package structure.
- Command-line interface.
- Version information.
- Automated tests.
- Development tooling.

Git operations, AI integration and the VS Code extension are planned for subsequent development phases.

## Installation

Clone the repository:

    git clone https://github.com/EgueRichnel2025/gitmind.git
    cd gitmind

Create a virtual environment:

    python -m venv .venv

Activate it on Windows Git Bash:

    source .venv/Scripts/activate

Install GitMind in development mode:

    pip install -e ".[dev]"

## Usage

Display help:

    gitmind --help

Display the current version:

    gitmind --version

Run as a Python module:

    python -m gitmind

## Development

Run tests:

    pytest -v

Check code quality:

    ruff check .
    ruff format --check .

## Planned Features

- Interactive modified-file selection.
- Paginated file navigation.
- Git status and diff analysis.
- AI-powered commit message generation.
- Interactive staging and commit creation.
- Optional Git push.
- VS Code extension.
- Multiple AI providers.

## License

License to be determined.
