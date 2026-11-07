"""Tests for the OpenAI-compatible AI provider."""

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from gitmind.core.ai import (
    AIAuthenticationError,
    AIConnectionError,
    AIProviderConfig,
    AIRateLimitError,
    AIRequestError,
    AIResponseError,
    AITimeoutError,
    OpenAICompatibleProvider,
)

API_KEY = "test-secret-api-key"


@pytest.fixture
def config() -> AIProviderConfig:
    return AIProviderConfig(
        api_key=API_KEY,
        model="test-model",
    )


@pytest.fixture
def provider(config: AIProviderConfig) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(config)


class FakeResponse(io.BytesIO):
    """Simulate a successful HTTP response."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


def make_response(content: str = "feat(auth): add authentication") -> bytes:
    """Build a valid Chat Completions response."""
    return json.dumps(
        {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ]
        }
    ).encode("utf-8")


def make_http_error(status_code: int) -> HTTPError:
    return HTTPError(
        url="https://provider.example/v1/chat/completions",
        code=status_code,
        msg="Simulated HTTP error",
        hdrs={},
        fp=io.BytesIO(b'{"error":"simulated"}'),
    )


def test_provider_generates_text(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/chat/completions")
        assert timeout == 30.0

        return FakeResponse(make_response())

    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        fake_urlopen,
    )

    result = provider.generate(
        system_prompt="You are a commit assistant.",
        user_prompt="Analyze the authentication changes.",
    )

    assert result == "feat(auth): add authentication"


def test_provider_sends_correct_http_request(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout

        return FakeResponse(make_response())

    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        fake_urlopen,
    )

    provider.generate(
        "System instructions",
        "Analyze these changes",
    )

    request = captured["request"]
    payload = json.loads(request.data.decode("utf-8"))

    assert request.method == "POST"
    assert request.full_url == ("https://api.groq.com/openai/v1/chat/completions")
    assert request.get_header("Authorization") == f"Bearer {API_KEY}"
    assert request.get_header("User-agent") == "GitMind/0.1.0"
    assert request.get_header("Content-type") == "application/json"
    assert payload["model"] == "test-model"
    assert payload["messages"] == [
        {
            "role": "system",
            "content": "System instructions",
        },
        {
            "role": "user",
            "content": "Analyze these changes",
        },
    ]
    assert payload["max_completion_tokens"] == 256
    assert payload["temperature"] == 0.2
    assert payload["stream"] is False


def test_provider_uses_custom_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_config = AIProviderConfig(
        api_key=API_KEY,
        model="custom-model",
        base_url="https://example.com/v1",
        timeout_seconds=45,
        max_completion_tokens=512,
        temperature=0.5,
    )

    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout

        return FakeResponse(make_response())

    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        fake_urlopen,
    )

    OpenAICompatibleProvider(custom_config).generate(
        "System",
        "User",
    )

    payload = json.loads(captured["request"].data.decode("utf-8"))

    assert captured["request"].full_url == ("https://example.com/v1/chat/completions")
    assert captured["timeout"] == 45.0
    assert payload["model"] == "custom-model"
    assert payload["max_completion_tokens"] == 512
    assert payload["temperature"] == 0.5


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, AIAuthenticationError),
        (403, AIAuthenticationError),
        (429, AIRateLimitError),
        (400, AIRequestError),
        (404, AIRequestError),
        (500, AIRequestError),
        (503, AIRequestError),
    ],
)
def test_provider_maps_http_errors(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_error: type[Exception],
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(make_http_error(status_code)),
    )

    with pytest.raises(expected_error):
        provider.generate("System", "User")


def test_provider_does_not_expose_api_key_in_http_errors(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(make_http_error(401)),
    )

    with pytest.raises(AIAuthenticationError) as error:
        provider.generate("System", "User")

    assert API_KEY not in str(error.value)


def test_provider_handles_timeout(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("simulated timeout")),
    )

    with pytest.raises(AITimeoutError):
        provider.generate("System", "User")


def test_provider_handles_socket_timeout(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("simulated timeout")),
    )

    with pytest.raises(AITimeoutError):
        provider.generate("System", "User")


def test_provider_handles_connection_errors(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError("network unavailable")),
    )

    with pytest.raises(AIConnectionError):
        provider.generate("System", "User")


def test_provider_detects_timeout_inside_url_error(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError(TimeoutError("simulated timeout"))),
    )

    with pytest.raises(AITimeoutError):
        provider.generate("System", "User")


@pytest.mark.parametrize(
    "raw_response",
    [
        b"not json",
        b"\xff\xfe",
        b"null",
        b"[]",
        b'{"choices":[]}',
        b'{"choices":[null]}',
        b'{"choices":[{}]}',
        b'{"choices":[{"message":null}]}',
        b'{"choices":[{"message":{"content":null}}]}',
        b'{"choices":[{"message":{"content":""}}]}',
        b'{"choices":[{"message":{"content":[]}}]}',
    ],
)
def test_provider_rejects_invalid_responses(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
    raw_response: bytes,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: FakeResponse(raw_response),
    )

    with pytest.raises(AIResponseError):
        provider.generate("System", "User")


def test_provider_rejects_oversized_response(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = b"x" * (provider.MAX_RESPONSE_BYTES + 1)

    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: FakeResponse(oversized),
    )

    with pytest.raises(AIResponseError, match="maximum allowed size"):
        provider.generate("System", "User")


@pytest.mark.parametrize(
    ("system_prompt", "user_prompt", "expected_error"),
    [
        ("", "User", ValueError),
        (" ", "User", ValueError),
        ("System", "", ValueError),
        ("System", " ", ValueError),
        (None, "User", TypeError),
        ("System", None, TypeError),
    ],
)
def test_provider_rejects_invalid_prompts(
    provider: OpenAICompatibleProvider,
    system_prompt: str | None,
    user_prompt: str | None,
    expected_error: type[Exception],
) -> None:
    with pytest.raises(expected_error):
        provider.generate(
            system_prompt,  # type: ignore[arg-type]
            user_prompt,  # type: ignore[arg-type]
        )


def test_provider_rejects_invalid_configuration() -> None:
    with pytest.raises(TypeError, match="AIProviderConfig"):
        OpenAICompatibleProvider(None)  # type: ignore[arg-type]


def test_provider_strips_response_whitespace(
    provider: OpenAICompatibleProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitmind.core.ai.provider.urlopen",
        lambda *args, **kwargs: FakeResponse(make_response("  feat(auth): add authentication  \n")),
    )

    result = provider.generate("System", "User")

    assert result == "feat(auth): add authentication"
