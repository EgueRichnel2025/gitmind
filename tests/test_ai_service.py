"""Tests for commit suggestion generation service."""

import json

import pytest

from gitmind.core.ai import (
    AIInvalidSuggestionsError,
    AIProviderConfig,
    AIProviderError,
    CommitSuggestionService,
    OpenAICompatibleProvider,
)
from gitmind.core.analysis.models import (
    FileAnalysis,
    FileAnalysisSnapshot,
)
from gitmind.core.git.status_models import GitFileStatus

VALID_MESSAGES = [
    "feat(auth): implement authentication",
    "refactor(auth): simplify authentication flow",
    "test(auth): add authentication tests",
]


class FakeProvider:
    """Simulate a text generation provider."""

    def __init__(self, response: object) -> None:
        self.response = response
        self.system_prompt = None
        self.user_prompt = None
        self.call_count = 0

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

        if isinstance(self.response, Exception):
            raise self.response

        return self.response  # type: ignore[return-value]


def make_analysis() -> FileAnalysisSnapshot:
    """Create a valid analysis snapshot."""
    return FileAnalysisSnapshot(
        files=(
            FileAnalysis(
                git_file=GitFileStatus("src/auth.py", " ", "M"),
                unstaged_diff="@@ -1 +1 @@\n-old\n+new",
            ),
        )
    )


def make_response(messages: list[str] | None = None) -> str:
    """Build a valid JSON suggestion response."""
    return json.dumps({"suggestions": VALID_MESSAGES if messages is None else messages})


def make_service(response: object) -> tuple[CommitSuggestionService, FakeProvider]:
    provider = FakeProvider(response)
    return CommitSuggestionService(provider), provider


def test_service_returns_three_suggestions() -> None:
    service, _ = make_service(make_response())

    result = service.generate(make_analysis())

    assert len(result.suggestions) == 3
    assert result.messages == tuple(VALID_MESSAGES)


def test_service_preserves_suggestion_order() -> None:
    service, _ = make_service(make_response())

    result = service.generate(make_analysis())

    assert result.messages[0] == VALID_MESSAGES[0]
    assert result.messages[1] == VALID_MESSAGES[1]
    assert result.messages[2] == VALID_MESSAGES[2]


def test_service_sends_built_prompts_to_provider() -> None:
    service, provider = make_service(make_response())

    service.generate(make_analysis())

    assert provider.call_count == 1
    assert provider.system_prompt is not None
    assert "exactly three" in provider.system_prompt.lower()
    assert provider.user_prompt is not None
    assert "src/auth.py" in provider.user_prompt


def test_service_accepts_markdown_json_fence() -> None:
    response = f"```json\n{make_response()}\n```"
    service, _ = make_service(response)

    result = service.generate(make_analysis())

    assert result.messages == tuple(VALID_MESSAGES)


def test_service_accepts_plain_markdown_fence() -> None:
    response = f"```\n{make_response()}\n```"
    service, _ = make_service(response)

    result = service.generate(make_analysis())

    assert result.messages == tuple(VALID_MESSAGES)


@pytest.mark.parametrize(
    "response",
    [
        "",
        "   ",
        "Here are your suggestions.",
        '{"suggestions": [',
        "null",
        "[]",
        "123",
    ],
)
def test_service_rejects_invalid_json_responses(response: str) -> None:
    service, _ = make_service(response)

    with pytest.raises(AIInvalidSuggestionsError):
        service.generate(make_analysis())


@pytest.mark.parametrize(
    "messages",
    [
        [],
        ["feat: add feature"],
        ["feat: add feature", "fix: correct bug"],
        [
            "feat: add feature",
            "fix: correct bug",
            "docs: update docs",
            "test: add tests",
        ],
    ],
)
def test_service_rejects_invalid_suggestion_count(
    messages: list[str],
) -> None:
    service, _ = make_service(make_response(messages))

    with pytest.raises(
        AIInvalidSuggestionsError,
        match="exactly three",
    ):
        service.generate(make_analysis())


@pytest.mark.parametrize(
    "messages",
    [
        [123, VALID_MESSAGES[1], VALID_MESSAGES[2]],
        ["", VALID_MESSAGES[1], VALID_MESSAGES[2]],
        ["   ", VALID_MESSAGES[1], VALID_MESSAGES[2]],
        ["message\ninjection", VALID_MESSAGES[1], VALID_MESSAGES[2]],
        [" message", VALID_MESSAGES[1], VALID_MESSAGES[2]],
    ],
)
def test_service_rejects_invalid_message_values(
    messages: list[object],
) -> None:
    service, _ = make_service(make_response(messages))  # type: ignore[arg-type]

    with pytest.raises(AIInvalidSuggestionsError):
        service.generate(make_analysis())


def test_service_rejects_duplicate_suggestions() -> None:
    messages = [
        "feat(auth): add login",
        "fix(auth): handle errors",
        "FEAT(AUTH): ADD LOGIN",
    ]

    service, _ = make_service(make_response(messages))

    with pytest.raises(AIInvalidSuggestionsError, match="Duplicate"):
        service.generate(make_analysis())


def test_service_rejects_additional_json_fields() -> None:
    response = json.dumps(
        {
            "suggestions": VALID_MESSAGES,
            "explanation": "Additional unexpected field",
        }
    )

    service, _ = make_service(response)

    with pytest.raises(AIInvalidSuggestionsError, match="exactly"):
        service.generate(make_analysis())


def test_service_rejects_missing_suggestions_field() -> None:
    service, _ = make_service('{"messages": []}')

    with pytest.raises(AIInvalidSuggestionsError):
        service.generate(make_analysis())


def test_service_rejects_non_string_provider_response() -> None:
    service, _ = make_service(None)

    with pytest.raises(AIInvalidSuggestionsError):
        service.generate(make_analysis())


def test_service_propagates_provider_errors() -> None:
    service, _ = make_service(AIProviderError("simulated provider failure"))

    with pytest.raises(AIProviderError, match="simulated"):
        service.generate(make_analysis())


def test_service_does_not_call_provider_for_empty_analysis() -> None:
    provider = FakeProvider(make_response())
    service = CommitSuggestionService(provider)

    empty_analysis = FileAnalysisSnapshot(files=())

    from gitmind.core.ai import AIContextError

    with pytest.raises(AIContextError):
        service.generate(empty_analysis)

    assert provider.call_count == 0


def test_service_rejects_provider_without_generate_method() -> None:
    with pytest.raises(TypeError, match="generate"):
        CommitSuggestionService(None)  # type: ignore[arg-type]


def test_service_rejects_invalid_provider_response_type() -> None:
    service, _ = make_service(123)

    with pytest.raises(AIInvalidSuggestionsError):
        service.generate(make_analysis())


def test_service_accepts_real_provider_interface() -> None:
    config = AIProviderConfig(
        api_key="test-key",
        model="test-model",
    )
    provider = OpenAICompatibleProvider(config)

    service = CommitSuggestionService(provider)

    assert isinstance(service, CommitSuggestionService)
