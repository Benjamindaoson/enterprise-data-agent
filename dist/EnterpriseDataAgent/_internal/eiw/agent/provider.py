"""Model Provider - LLM provider abstraction for Enterprise Data Agent.

This module provides:
- Abstract provider contract
- Deterministic provider for testing
- Anthropic/Anthropic API provider
- Timeout and retry handling
- Token usage tracking
- OpenTelemetry tracing
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")

import structlog

from eiw.observability.otel import trace_span, get_correlation_context
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "model_provider")


# =============================================================================
# Provider Types and Enums
# =============================================================================


class ProviderType(str, Enum):
    """Model provider types."""

    DETERMINISTIC = "deterministic"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    BEDROCK = "bedrock"


class ModelFamily(str, Enum):
    """Model families."""

    CLAUDE = "claude"
    GPT = "gpt"
    GEMINI = "gemini"


@dataclass
class ModelInfo:
    """Information about a model."""

    provider: str
    model_name: str
    family: str
    max_tokens: int = 8192
    supports_structured_output: bool = True
    supports_vision: bool = False
    context_window: int = 200000


@dataclass
class TokenUsage:
    """Token usage tracking."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Tokens(prompt={self.prompt_tokens}, completion={self.completion_tokens}, total={self.total_tokens})"


@dataclass
class ProviderResponse:
    """Base response from a model provider."""

    content: str
    usage: TokenUsage | None = None
    model: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    trace_id: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None


@dataclass
class StructuredResponse(Generic[T]):
    """Response with structured output parsing."""

    data: T | None
    raw_content: str
    parse_error: str | None = None
    usage: TokenUsage | None = None
    success: bool = True


class ProviderError(Exception):
    """Base provider error."""

    def __init__(
        self,
        message: str,
        error_type: str = "provider_error",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.retryable = retryable


class TimeoutError(ProviderError):
    """Provider timeout error."""

    def __init__(self, message: str = "Provider request timed out"):
        super().__init__(message, error_type="timeout", retryable=True)


class RateLimitError(ProviderError):
    """Provider rate limit error."""

    def __init__(self, message: str = "Provider rate limit exceeded"):
        super().__init__(message, error_type="rate_limit", retryable=True)


class AuthenticationError(ProviderError):
    """Provider authentication error."""

    def __init__(self, message: str = "Provider authentication failed"):
        super().__init__(message, error_type="authentication", retryable=False)


class InvalidRequestError(ProviderError):
    """Provider invalid request error."""

    def __init__(self, message: str = "Invalid provider request"):
        super().__init__(message, error_type="invalid_request", retryable=False)


# =============================================================================
# Provider Configuration
# =============================================================================


@dataclass
class ProviderConfig:
    """Configuration for model provider."""

    provider_type: ProviderType = ProviderType.DETERMINISTIC
    model_name: str = "claude-sonnet-4-20250514"
    api_key: str | None = None
    api_base: str | None = None
    max_retries: int = 3
    timeout_seconds: float = 60.0
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 4096
    prompt_version: str = "1.0"

    def get_model_info(self) -> ModelInfo:
        """Get model information based on config."""
        family = ModelFamily.CLAUDE.value if "claude" in self.model_name.lower() else ModelFamily.GPT.value
        # Handle both enum and string provider_type
        provider = self.provider_type.value if hasattr(self.provider_type, 'value') else str(self.provider_type)
        return ModelInfo(
            provider=provider,
            model_name=self.model_name,
            family=family,
            supports_structured_output=True,
        )


# =============================================================================
# Abstract Provider Interface
# =============================================================================


class ModelProvider(ABC):
    """Abstract interface for model providers."""

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._model_info = config.get_model_info()
        self._total_usage = TokenUsage()

    @property
    def config(self) -> ProviderConfig:
        return self._config

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    @property
    def total_usage(self) -> TokenUsage:
        return self._total_usage

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        """Generate a completion.

        Args:
            prompt: User prompt
            system: System prompt
            temperature: Override default temperature
            max_tokens: Override max tokens

        Returns:
            Provider response
        """
        raise NotImplementedError

    @abstractmethod
    async def structured_complete[T](
        self,
        prompt: str,
        response_model: type[T],
        system: str | None = None,
        temperature: float | None = None,
    ) -> StructuredResponse[T]:
        """Generate a completion with structured output.

        Args:
            prompt: User prompt
            response_model: Pydantic model for response
            system: System prompt
            temperature: Override default temperature

        Returns:
            Structured response
        """
        raise NotImplementedError

    def _get_trace_context(self) -> dict[str, Any]:
        """Get trace context for spans."""
        try:
            ctx = get_correlation_context()
            return {
                "provider": self._config.provider_type.value,
                "model": self._config.model_name,
                "prompt_version": self._config.prompt_version,
                "correlation_id": ctx.correlation_id if ctx else None,
            }
        except Exception:
            return {
                "provider": self._config.provider_type.value,
                "model": self._config.model_name,
                "prompt_version": self._config.prompt_version,
            }


# =============================================================================
# Deterministic Provider (for testing)
# =============================================================================


class DeterministicProvider(ModelProvider):
    """Deterministic provider for reproducible testing.

    This provider returns predefined responses based on prompt matching.
    Use for CI/CD and test environments.
    """

    def __init__(self, config: ProviderConfig | None = None):
        super().__init__(config or ProviderConfig())
        self._responses: dict[str, str] = {}
        self._structured_responses: dict[str, dict[str, Any]] = {}

    def add_response(self, prompt_substring: str, response: str) -> None:
        """Add a deterministic response for a prompt pattern.

        Args:
            prompt_substring: Substring to match in prompt
            response: Response to return
        """
        self._responses[prompt_substring.lower()] = response

    def add_structured_response(
        self,
        prompt_substring: str,
        data: dict[str, Any],
    ) -> None:
        """Add a deterministic structured response.

        Args:
            prompt_substring: Substring to match in prompt
            data: Structured data to return
        """
        self._structured_responses[prompt_substring.lower()] = data

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        """Generate deterministic completion."""
        trace_ctx = self._get_trace_context()
        start = datetime.now()

        with trace_span("provider.complete", {**trace_ctx, "prompt_length": len(prompt)}):
            # Look for matching response
            response = self._find_response(prompt)

            if response is None:
                # Return a default structured response
                response = '{"intent": "unknown", "confidence": 0.0}'

            usage = TokenUsage(
                prompt_tokens=len(prompt) // 4,  # Rough estimate
                completion_tokens=len(response) // 4,
                total_tokens=(len(prompt) + len(response)) // 4,
            )
            self._total_usage.prompt_tokens += usage.prompt_tokens
            self._total_usage.completion_tokens += usage.completion_tokens
            self._total_usage.total_tokens += usage.total_tokens

            latency_ms = (datetime.now() - start).total_seconds() * 1000

            logger.info(
                "Deterministic provider response",
                extra={**trace_ctx, "latency_ms": latency_ms, "usage": str(usage)}
            )

            return ProviderResponse(
                content=response,
                usage=usage,
                model=self._model_info.model_name,
                provider=self._model_info.provider,
                latency_ms=latency_ms,
                trace_id=trace_ctx.get("correlation_id"),
                error=None,  # Always explicitly set error to None for successful response
            )

    async def structured_complete[T](
        self,
        prompt: str,
        response_model: type[T],
        system: str | None = None,
        temperature: float | None = None,
    ) -> StructuredResponse[T]:
        """Generate deterministic structured completion."""
        from pydantic import BaseModel

        trace_ctx = self._get_trace_context()
        start = datetime.now()

        with trace_span("provider.structured_complete", {**trace_ctx, "model": response_model.__name__}):
            # Find structured response
            raw_content = None
            for pattern, data in self._structured_responses.items():
                if pattern.lower() in prompt.lower():
                    import json
                    raw_content = json.dumps(data)
                    break

            if raw_content is None:
                return StructuredResponse(
                    data=None,
                    raw_content="",
                    parse_error="No matching deterministic response found",
                    success=False,
                )

            # Parse into model
            try:
                data = response_model.model_validate_json(raw_content)
                return StructuredResponse(
                    data=data,
                    raw_content=raw_content,
                    success=True,
                )
            except Exception as e:
                return StructuredResponse(
                    data=None,
                    raw_content=raw_content,
                    parse_error=str(e),
                    success=False,
                )

    def _find_response(self, prompt: str) -> str | None:
        """Find matching response for prompt."""
        prompt_lower = prompt.lower()
        for pattern, response in self._responses.items():
            if pattern in prompt_lower:
                return response
        return None


# =============================================================================
# Anthropic Provider
# =============================================================================


class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider.

    Requires ANTHROPIC_API_KEY environment variable.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            from anthropic import AsyncAnthropic
            api_key = self._config.api_key or __import__("os").getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set")
                return
            self._client = AsyncAnthropic(api_key=api_key, base_url=self._config.api_base)
        except ImportError:
            logger.warning("anthropic package not installed")

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        """Generate completion using Anthropic API."""
        import time

        trace_ctx = self._get_trace_context()
        start = time.time()

        if not self._client:
            return ProviderResponse(
                content="",
                error="Anthropic client not initialized",
                trace_id=trace_ctx.get("correlation_id"),
            )

        with trace_span("provider.complete", {**trace_ctx, "prompt_length": len(prompt)}):
            try:
                response = await self._client.messages.create(
                    model=self._config.model_name,
                    max_tokens=max_tokens or self._config.max_tokens,
                    temperature=temperature if temperature is not None else self._config.temperature,
                    system=system or "",
                    messages=[{"role": "user", "content": prompt}],
                )

                content = response.content[0].text if response.content else ""
                usage = TokenUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                )

                self._total_usage.prompt_tokens += usage.prompt_tokens
                self._total_usage.completion_tokens += usage.completion_tokens
                self._total_usage.total_tokens += usage.total_tokens

                latency_ms = (time.time() - start) * 1000

                return ProviderResponse(
                    content=content,
                    usage=usage,
                    model=self._model_info.model_name,
                    provider=self._model_info.provider,
                    latency_ms=latency_ms,
                    trace_id=trace_ctx.get("correlation_id"),
                )

            except Exception as e:
                logger.error(f"Anthropic API error: {e}")
                return ProviderResponse(
                    content="",
                    error=str(e),
                    latency_ms=(time.time() - start) * 1000,
                    trace_id=trace_ctx.get("correlation_id"),
                )

    async def structured_complete[T](
        self,
        prompt: str,
        response_model: type[T],
        system: str | None = None,
        temperature: float | None = None,
    ) -> StructuredResponse[T]:
        """Generate structured completion using Anthropic API."""
        import json

        trace_ctx = self._get_trace_context()

        # Use JSON output mode for structured responses
        response = await self.complete(
            prompt=prompt,
            system=f"{system or ''}\n\nRespond with valid JSON only, no markdown.",
            temperature=temperature,
            max_tokens=self._config.max_tokens,
        )

        if response.error:
            return StructuredResponse(
                data=None,
                raw_content="",
                parse_error=response.error,
                success=False,
            )

        try:
            # Try to extract JSON from response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = response_model.model_validate_json(content)
            return StructuredResponse(
                data=data,
                raw_content=content,
                usage=response.usage,
                success=True,
            )
        except Exception as e:
            return StructuredResponse(
                data=None,
                raw_content=response.content,
                parse_error=str(e),
                usage=response.usage,
                success=False,
            )


# =============================================================================
# Provider Factory
# =============================================================================


def create_provider(config: ProviderConfig | None = None) -> ModelProvider:
    """Create a model provider based on configuration.

    Args:
        config: Provider configuration

    Returns:
        Model provider instance
    """
    config = config or ProviderConfig()

    if config.provider_type == ProviderType.DETERMINISTIC:
        return DeterministicProvider(config)
    elif config.provider_type == ProviderType.ANTHROPIC:
        return AnthropicProvider(config)
    else:
        raise ValueError(f"Unknown provider type: {config.provider_type}")


def get_default_provider() -> ModelProvider:
    """Get default provider from environment or config."""
    import os

    provider_type = os.getenv("EIW_MODEL_PROVIDER", "deterministic")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    config = ProviderConfig(
        provider_type=ProviderType(provider_type),
        api_key=api_key,
    )

    return create_provider(config)
