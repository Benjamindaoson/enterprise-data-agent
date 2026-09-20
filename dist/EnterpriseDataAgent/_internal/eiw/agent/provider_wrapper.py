"""Provider Wrapper with Billing Integration.

Provides a wrapper around ModelProvider that automatically records
costs to the billing service.
"""

from __future__ import annotations

from typing import Any, TypeVar

from eiw.agent.provider import (
    ModelProvider,
    ProviderResponse,
    StructuredResponse,
    TokenUsage,
)
from eiw.billing.service import get_billing_service
from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "provider_wrapper")

T = TypeVar("T")


class BillingProviderWrapper(ModelProvider):
    """Wrapper that adds billing tracking to any provider.

    Automatically records costs for every API call.
    """

    def __init__(
        self,
        provider: ModelProvider,
        task_id: str | None = None,
    ):
        """Initialize wrapper.

        Args:
            provider: Underlying provider
            task_id: Optional task ID for cost attribution
        """
        self._provider = provider
        self._task_id = task_id
        self._billing = get_billing_service()

    @property
    def config(self):
        return self._provider.config

    @property
    def model_info(self):
        return self._provider.model_info

    @property
    def total_usage(self) -> TokenUsage:
        return self._provider.total_usage

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        """Complete with billing tracking."""
        response = await self._provider.complete(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Record cost if usage is available
        if response.usage and not response.error:
            self._billing.record_cost(
                usage=response.usage,
                model_name=response.model or self._provider.model_info.model_name,
                provider=response.provider or self._provider.model_info.provider,
                task_id=self._task_id,
                metadata={
                    "latency_ms": response.latency_ms,
                    "prompt_length": len(prompt),
                },
            )

        return response

    async def structured_complete[T](
        self,
        prompt: str,
        response_model: type[T],
        system: str | None = None,
        temperature: float | None = None,
    ) -> StructuredResponse[T]:
        """Structured complete with billing tracking."""
        response = await self._provider.structured_complete(
            prompt=prompt,
            response_model=response_model,
            system=system,
            temperature=temperature,
        )

        # Record cost if usage is available
        if response.usage and response.success:
            self._billing.record_cost(
                usage=response.usage,
                model_name=self._provider.model_info.model_name,
                provider=self._provider.model_info.provider,
                task_id=self._task_id,
                metadata={
                    "response_model": response_model.__name__,
                },
            )

        return response

    def set_task_id(self, task_id: str) -> None:
        """Set task ID for cost attribution."""
        self._task_id = task_id


def wrap_provider(
    provider: ModelProvider,
    task_id: str | None = None,
) -> ModelProvider:
    """Wrap a provider with billing tracking.

    Args:
        provider: Provider to wrap
        task_id: Optional task ID

    Returns:
        Wrapped provider with billing
    """
    return BillingProviderWrapper(provider, task_id)
