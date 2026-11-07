"""Application service for generating commit message suggestions."""

import json
from collections.abc import Mapping
from typing import Protocol

from gitmind.core.ai.errors import AIInvalidSuggestionsError
from gitmind.core.ai.models import (
    CommitSuggestion,
    CommitSuggestionSet,
)
from gitmind.core.ai.prompts import CommitPromptBuilder
from gitmind.core.analysis.models import FileAnalysisSnapshot


class TextGenerationProvider(Protocol):
    """Define the interface required by a text generation provider."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text from system and user prompts."""
        ...


class CommitSuggestionService:
    """Generate and validate three commit messages from Git analysis."""

    def __init__(
        self,
        provider: TextGenerationProvider,
        prompt_builder: CommitPromptBuilder | None = None,
    ) -> None:
        if not callable(getattr(provider, "generate", None)):
            raise TypeError("provider must expose a callable generate method.")

        if prompt_builder is not None and not isinstance(prompt_builder, CommitPromptBuilder):
            raise TypeError("prompt_builder must be a CommitPromptBuilder.")

        self._provider = provider
        self._prompt_builder = (
            prompt_builder if prompt_builder is not None else CommitPromptBuilder()
        )

    def generate(
        self,
        analysis: FileAnalysisSnapshot,
    ) -> CommitSuggestionSet:
        """Generate exactly three validated commit suggestions."""
        prompt = self._prompt_builder.build(analysis)

        response = self._provider.generate(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )

        return self._parse_response(response)

    @classmethod
    def _parse_response(cls, response: str) -> CommitSuggestionSet:
        """Parse and validate the provider JSON response."""
        if not isinstance(response, str):
            raise AIInvalidSuggestionsError("AI provider response must be a string.")

        normalized = response.strip()

        if not normalized:
            raise AIInvalidSuggestionsError("AI provider returned an empty suggestion response.")

        normalized = cls._remove_json_fence(normalized)

        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise AIInvalidSuggestionsError(
                "AI provider did not return valid JSON suggestions."
            ) from exc

        if not isinstance(payload, Mapping):
            raise AIInvalidSuggestionsError("Suggestion response must be a JSON object.")

        if set(payload.keys()) != {"suggestions"}:
            raise AIInvalidSuggestionsError(
                "Suggestion response must contain exactly the 'suggestions' field."
            )

        messages = payload["suggestions"]

        if not isinstance(messages, list) or len(messages) != 3:
            raise AIInvalidSuggestionsError("AI provider must return exactly three suggestions.")

        try:
            suggestions = tuple(CommitSuggestion(message=message) for message in messages)

            return CommitSuggestionSet(suggestions=suggestions)

        except (TypeError, ValueError) as exc:
            raise AIInvalidSuggestionsError(
                f"AI provider returned invalid commit suggestions: {exc}"
            ) from exc

    @staticmethod
    def _remove_json_fence(response: str) -> str:
        """Remove an optional Markdown JSON code fence."""
        lines = response.splitlines()

        if (
            len(lines) >= 3
            and lines[0].strip().lower() in {"```", "```json"}
            and lines[-1].strip() == "```"
        ):
            return "\n".join(lines[1:-1]).strip()

        return response
