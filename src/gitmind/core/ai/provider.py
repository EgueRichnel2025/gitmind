"""HTTP client for OpenAI-compatible AI providers."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from gitmind.core.ai.config import AIProviderConfig
from gitmind.core.ai.errors import (
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
    AIRequestError,
    AIResponseError,
    AITimeoutError,
)


class OpenAICompatibleProvider:
    """Send chat completion requests to an OpenAI-compatible API."""

    MAX_RESPONSE_BYTES = 2_000_000

    def __init__(self, config: AIProviderConfig) -> None:
        if not isinstance(config, AIProviderConfig):
            raise TypeError("config must be an AIProviderConfig instance.")

        self._config = config
        self._endpoint = f"{config.base_url}/chat/completions"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate text from a system prompt and a user prompt."""
        self._validate_prompt(system_prompt, "system_prompt")
        self._validate_prompt(user_prompt, "user_prompt")

        payload = {
            "model": self._config.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt.strip(),
                },
                {
                    "role": "user",
                    "content": user_prompt.strip(),
                },
            ],
            "temperature": self._config.temperature,
            "max_completion_tokens": self._config.max_completion_tokens,
            "stream": False,
        }

        request = Request(
            url=self._endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self._config.timeout_seconds,
            ) as response:
                raw_response = response.read(self.MAX_RESPONSE_BYTES + 1)

        except HTTPError as exc:
            self._handle_http_error(exc)

        except TimeoutError as exc:
            raise AITimeoutError("AI provider request timed out.") from exc

        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise AITimeoutError("AI provider request timed out.") from exc

            raise AIConnectionError("Unable to connect to the AI provider.") from exc

        except OSError as exc:
            raise AIConnectionError("Unable to communicate with the AI provider.") from exc

        if len(raw_response) > self.MAX_RESPONSE_BYTES:
            raise AIResponseError("AI provider response exceeds the maximum allowed size.")

        return self._extract_content(raw_response)

    @staticmethod
    def _validate_prompt(value: str, field_name: str) -> None:
        """Validate a prompt before sending it to the provider."""
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")

        if not value.strip():
            raise ValueError(f"{field_name} cannot be empty.")

    @staticmethod
    def _handle_http_error(error: HTTPError) -> None:
        """Map HTTP errors to explicit provider exceptions."""
        status_code = error.code

        if status_code in {401, 403}:
            raise AIAuthenticationError(
                f"AI provider authentication failed (HTTP {status_code})."
            ) from error

        if status_code == 429:
            raise AIRateLimitError("AI provider rate limit reached (HTTP 429).") from error

        raise AIRequestError(f"AI provider rejected the request (HTTP {status_code}).") from error

    @staticmethod
    def _extract_content(raw_response: bytes) -> str:
        """Extract generated text from a Chat Completions JSON response."""
        try:
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AIResponseError("AI provider returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise AIResponseError("AI provider response must be a JSON object.")

        choices = payload.get("choices")

        if not isinstance(choices, list) or not choices:
            raise AIResponseError("AI provider response does not contain any choices.")

        first_choice = choices[0]

        if not isinstance(first_choice, dict):
            raise AIResponseError("AI provider returned an invalid choice.")

        message = first_choice.get("message")

        if not isinstance(message, dict):
            raise AIResponseError("AI provider response does not contain a valid message.")

        content = message.get("content")

        if not isinstance(content, str) or not content.strip():
            raise AIResponseError("AI provider returned empty or non-text content.")

        return content.strip()
