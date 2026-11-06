"""Tests for AI provider configuration."""

from dataclasses import FrozenInstanceError

import pytest

from gitmind.core.ai import (
    AIConfigurationError,
    AIProviderConfig,
)

VALID_ENV = {
    "GITMIND_AI_API_KEY": "test-secret-key",
    "GITMIND_AI_MODEL": "test-model",
}


def make_config(**overrides: object) -> AIProviderConfig:
    values = {
        "api_key": "test-secret-key",
        "model": "test-model",
    }
    values.update(overrides)
    return AIProviderConfig(**values)  # type: ignore[arg-type]


def test_config_accepts_valid_values() -> None:
    config = make_config()

    assert config.api_key == "test-secret-key"
    assert config.model == "test-model"
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.timeout_seconds == 30.0
    assert config.max_completion_tokens == 256
    assert config.temperature == 0.2


def test_config_strips_api_key_and_model_whitespace() -> None:
    config = make_config(
        api_key="  secret-key  ",
        model="  example-model  ",
    )

    assert config.api_key == "secret-key"
    assert config.model == "example-model"


def test_config_does_not_expose_api_key_in_repr() -> None:
    config = make_config()

    assert "test-secret-key" not in repr(config)


def test_config_is_immutable() -> None:
    config = make_config()

    with pytest.raises(FrozenInstanceError):
        config.model = "another-model"  # type: ignore[misc]


@pytest.mark.parametrize(
    "api_key",
    ["", " ", None, 123],
)
def test_config_rejects_invalid_api_key(api_key: object) -> None:
    with pytest.raises(AIConfigurationError, match="API key"):
        make_config(api_key=api_key)


@pytest.mark.parametrize(
    "model",
    ["", " ", None, 123, "model\ninjection"],
)
def test_config_rejects_invalid_model(model: object) -> None:
    with pytest.raises(AIConfigurationError, match="model"):
        make_config(model=model)


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        "not-a-url",
        "ftp://provider.example/v1",
        "https:///missing-host",
        "https://user:password@example.com/v1",
        "https://provider.example/v1?token=secret",
        "https://provider.example/v1#fragment",
        "http://provider.example/v1",
    ],
)
def test_config_rejects_invalid_base_urls(base_url: str) -> None:
    with pytest.raises(AIConfigurationError):
        make_config(base_url=base_url)


def test_config_allows_local_http_provider() -> None:
    config = make_config(base_url="http://localhost:8080/v1/")

    assert config.base_url == "http://localhost:8080/v1"


@pytest.mark.parametrize(
    "timeout",
    [0, -1, True, float("inf"), float("nan"), "30"],
)
def test_config_rejects_invalid_timeout(timeout: object) -> None:
    with pytest.raises(AIConfigurationError, match="timeout"):
        make_config(timeout_seconds=timeout)


@pytest.mark.parametrize(
    "max_tokens",
    [0, -1, True, 1.5, "256"],
)
def test_config_rejects_invalid_max_completion_tokens(
    max_tokens: object,
) -> None:
    with pytest.raises(AIConfigurationError, match="tokens"):
        make_config(max_completion_tokens=max_tokens)


@pytest.mark.parametrize(
    "temperature",
    [-0.1, 2.1, True, float("inf"), float("nan"), "0.2"],
)
def test_config_rejects_invalid_temperature(temperature: object) -> None:
    with pytest.raises(AIConfigurationError, match="temperature"):
        make_config(temperature=temperature)


def test_config_loads_environment_values() -> None:
    config = AIProviderConfig.from_env(VALID_ENV)

    assert config.api_key == "test-secret-key"
    assert config.model == "test-model"


def test_config_loads_custom_environment_values() -> None:
    config = AIProviderConfig.from_env(
        {
            **VALID_ENV,
            "GITMIND_AI_BASE_URL": "https://example.com/v1",
            "GITMIND_AI_TIMEOUT_SECONDS": "45",
            "GITMIND_AI_MAX_COMPLETION_TOKENS": "512",
            "GITMIND_AI_TEMPERATURE": "0.4",
        }
    )

    assert config.base_url == "https://example.com/v1"
    assert config.timeout_seconds == 45.0
    assert config.max_completion_tokens == 512
    assert config.temperature == 0.4


def test_config_requires_api_key_environment_variable() -> None:
    with pytest.raises(AIConfigurationError, match="GITMIND_AI_API_KEY"):
        AIProviderConfig.from_env({"GITMIND_AI_MODEL": "test-model"})


def test_config_requires_model_environment_variable() -> None:
    with pytest.raises(AIConfigurationError, match="GITMIND_AI_MODEL"):
        AIProviderConfig.from_env({"GITMIND_AI_API_KEY": "secret"})


def test_config_rejects_invalid_numeric_environment_values() -> None:
    with pytest.raises(AIConfigurationError, match="numeric"):
        AIProviderConfig.from_env(
            {
                **VALID_ENV,
                "GITMIND_AI_TIMEOUT_SECONDS": "not-a-number",
            }
        )
