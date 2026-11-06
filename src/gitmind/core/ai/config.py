"""Configuration for OpenAI-compatible AI providers."""

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from gitmind.core.ai.errors import AIConfigurationError

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


@dataclass(frozen=True, slots=True)
class AIProviderConfig:
    """Immutable configuration for an AI provider."""

    api_key: str = field(repr=False)
    model: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 30.0
    max_completion_tokens: int = 256
    temperature: float = 0.2

    def __post_init__(self) -> None:
        self._validate_api_key()
        self._validate_model()
        self._validate_base_url()
        self._validate_timeout()
        self._validate_max_completion_tokens()
        self._validate_temperature()

    def _validate_api_key(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise AIConfigurationError("AI API key cannot be empty.")

        object.__setattr__(self, "api_key", self.api_key.strip())

    def _validate_model(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise AIConfigurationError("AI model cannot be empty.")

        if "\n" in self.model or "\r" in self.model:
            raise AIConfigurationError("AI model must be a single-line value.")

        object.__setattr__(self, "model", self.model.strip())

    def _validate_base_url(self) -> None:
        if not isinstance(self.base_url, str) or not self.base_url.strip():
            raise AIConfigurationError("AI base URL cannot be empty.")

        value = self.base_url.strip().rstrip("/")

        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
        except ValueError as exc:
            raise AIConfigurationError("AI base URL is invalid.") from exc

        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.netloc
            or hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise AIConfigurationError("AI base URL is invalid.")

        # Plain HTTP is permitted only for local development servers.
        if parsed.scheme == "http" and hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise AIConfigurationError("HTTP is only permitted for localhost AI providers.")

        object.__setattr__(self, "base_url", value)

    def _validate_timeout(self) -> None:
        value = self.timeout_seconds

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise AIConfigurationError("AI timeout must be a positive finite number.")

        object.__setattr__(self, "timeout_seconds", float(value))

    def _validate_max_completion_tokens(self) -> None:
        value = self.max_completion_tokens

        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise AIConfigurationError("Maximum completion tokens must be a positive integer.")

    def _validate_temperature(self) -> None:
        value = self.temperature

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 2
        ):
            raise AIConfigurationError("AI temperature must be a finite number between 0 and 2.")

        object.__setattr__(self, "temperature", float(value))

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "AIProviderConfig":
        """Build the provider configuration from environment variables."""
        values = os.environ if env is None else env

        api_key = values.get("GITMIND_AI_API_KEY")
        model = values.get("GITMIND_AI_MODEL")

        if not api_key or not api_key.strip():
            raise AIConfigurationError("Missing GITMIND_AI_API_KEY environment variable.")

        if not model or not model.strip():
            raise AIConfigurationError("Missing GITMIND_AI_MODEL environment variable.")

        try:
            timeout = float(values.get("GITMIND_AI_TIMEOUT_SECONDS", "30"))
            max_tokens = int(values.get("GITMIND_AI_MAX_COMPLETION_TOKENS", "256"))
            temperature = float(values.get("GITMIND_AI_TEMPERATURE", "0.2"))
        except ValueError as exc:
            raise AIConfigurationError(
                "One or more AI numeric configuration values are invalid."
            ) from exc

        return cls(
            api_key=api_key,
            model=model,
            base_url=values.get(
                "GITMIND_AI_BASE_URL",
                DEFAULT_BASE_URL,
            ),
            timeout_seconds=timeout,
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
