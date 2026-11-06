"""Exceptions raised by the AI integration layer."""


class AIConfigurationError(ValueError):
    """Raised when the AI provider configuration is invalid."""


class AIProviderError(RuntimeError):
    """Base exception for AI provider failures."""


class AIAuthenticationError(AIProviderError):
    """Raised when the provider rejects the API credentials."""


class AIRateLimitError(AIProviderError):
    """Raised when the provider rate limit is reached."""


class AIRequestError(AIProviderError):
    """Raised when the provider rejects or cannot process a request."""


class AIConnectionError(AIProviderError):
    """Raised when the provider cannot be reached."""


class AITimeoutError(AIConnectionError):
    """Raised when a provider request exceeds its timeout."""


class AIResponseError(AIProviderError):
    """Raised when the provider returns an invalid response."""
