"""Langfuse integration for LLM observability.

Provides:
- Tracing for LLM calls (prompts, completions, tokens)
- Span management for agent steps
- Dataset tracking for evaluations
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "langfuse")

# Lazy import to avoid hard dependency
_langfuse = None
_langfuse_available = False

try:
    import langfuse
    _langfuse_available = True
except ImportError:
    logger.warning("langfuse not installed. Run: pip install langfuse")


@dataclass
class LangfuseConfig:
    """Langfuse configuration."""

    public_key: str | None = None
    secret_key: str | None = None
    host: str = "https://cloud.langfuse.com"
    enabled: bool = False
    debug: bool = False
    sample_rate: float = 1.0  # 0.0-1.0, sampling rate


@dataclass
class LLMPrompt:
    """LLM prompt trace."""

    name: str
    prompt: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMCompletion:
    """LLM completion trace."""

    prompt: str
    completion: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)  # input_tokens, output_tokens
    latency_ms: float = 0.0
    status: str = "success"
    error: str | None = None


class LangfuseTracer:
    """Langfuse tracer for LLM observability.

    Usage:
        tracer = LangfuseTracer()
        tracer.init()

        with tracer.trace("intent-resolution") as span:
            span.log_prompt(prompt)
            result = llm.complete(prompt)
            span.log_completion(result)
    """

    def __init__(self, config: LangfuseConfig | None = None):
        self._config = config or self._load_config()
        self._client = None
        self._initialized = False

    def _load_config(self) -> LangfuseConfig:
        """Load config from environment."""
        return LangfuseConfig(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            enabled=os.getenv("LANGFUSE_ENABLED", "false").lower() == "true",
            debug=os.getenv("LANGFUSE_DEBUG", "false").lower() == "true",
        )

    def init(self) -> bool:
        """Initialize Langfuse client.

        Returns:
            True if initialized successfully
        """
        if self._initialized:
            return True

        if not self._config.enabled:
            logger.debug("Langfuse disabled")
            return False

        if not _langfuse_available:
            logger.warning("Langfuse not available")
            return False

        if not self._config.public_key or not self._config.secret_key:
            logger.warning("Langfuse keys not configured")
            return False

        try:
            langfuse.auth_check(
                public_key=self._config.public_key,
                secret_key=self._config.secret_key,
                host=self._config.host,
            )
            self._client = langfuse
            self._initialized = True
            logger.info("Langfuse initialized")
            return True
        except Exception as e:
            logger.error(f"Langfuse init failed: {e}")
            return False

    @property
    def is_enabled(self) -> bool:
        """Check if Langfuse is enabled and initialized."""
        return self._initialized and self._client is not None

    def trace(self, name: str, **kwargs) -> "LangfuseSpan":
        """Start a new trace.

        Args:
            name: Trace name

        Returns:
            Span context manager
        """
        if not self.is_enabled:
            return _NoOpSpan()

        return LangfuseSpan(self._client, name, **kwargs)

    def log_prompt(self, prompt: LLMPrompt) -> None:
        """Log an LLM prompt.

        Args:
            prompt: Prompt details
        """
        if not self.is_enabled:
            return

        try:
            self._client.log_prompt(
                name=prompt.name,
                prompt=prompt.prompt,
                model=prompt.model,
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
                metadata=prompt.metadata,
            )
        except Exception as e:
            logger.warning(f"Failed to log prompt: {e}")

    def log_completion(self, completion: LLMCompletion) -> None:
        """Log an LLM completion.

        Args:
            completion: Completion details
        """
        if not self.is_enabled:
            return

        try:
            self._client.log_completion(
                completion=completion.completion,
                model=completion.model,
                usage=completion.usage,
                latency_ms=completion.latency_ms,
                status=completion.status,
                error=completion.error,
            )
        except Exception as e:
            logger.warning(f"Failed to log completion: {e}")


class LangfuseSpan:
    """Langfuse span context manager."""

    def __init__(self, client, name: str, **kwargs):
        self._client = client
        self._name = name
        self._kwargs = kwargs
        self._trace = None
        self._span = None

    def __enter__(self):
        if self._client:
            try:
                self._trace = self._client.trace(name=self._name, **self._kwargs)
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._span:
            if exc_type:
                self._span.end(error=str(exc_val))
            else:
                self._span.end()

    def log_prompt(self, prompt: LLMPrompt) -> None:
        """Log prompt within span."""
        if self._trace:
            try:
                self._trace.log_prompt(
                    name=prompt.name,
                    prompt=prompt.prompt,
                    model=prompt.model,
                )
            except Exception:
                pass

    def log_completion(self, completion: LLMCompletion) -> None:
        """Log completion within span."""
        if self._trace:
            try:
                self._trace.log_completion(
                    completion=completion.completion,
                    model=completion.model,
                    usage=completion.usage,
                )
            except Exception:
                pass


class _NoOpSpan:
    """No-op span for when Langfuse is disabled."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def log_prompt(self, *args, **kwargs):
        pass

    def log_completion(self, *args, **kwargs):
        pass


# Global tracer instance
_langfuse_tracer: LangfuseTracer | None = None


def get_langfuse_tracer() -> LangfuseTracer:
    """Get global Langfuse tracer instance."""
    global _langfuse_tracer
    if _langfuse_tracer is None:
        _langfuse_tracer = LangfuseTracer()
        _langfuse_tracer.init()
    return _langfuse_tracer
