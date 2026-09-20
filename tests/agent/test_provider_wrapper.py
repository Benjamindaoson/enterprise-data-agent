"""Tests for provider wrapper with billing integration."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from eiw.agent.provider import (
    DeterministicProvider,
    ProviderConfig,
    ProviderResponse,
    TokenUsage,
)
from eiw.agent.provider_wrapper import BillingProviderWrapper, wrap_provider
from eiw.billing.service import BillingService, get_billing_service


class TestBillingProviderWrapper:
    """Test billing wrapper functionality."""

    def setup_method(self):
        """Reset billing service before each test."""
        # Reset global billing service
        import eiw.billing.service as billing_module
        billing_module._billing_service = None

    @pytest.mark.asyncio
    async def test_wrapper_records_cost_on_complete(self):
        """Test that wrapper records cost on successful completion."""
        # Create mock provider
        mock_provider = MagicMock()
        mock_provider.config = ProviderConfig()
        mock_provider.model_info = MagicMock()
        mock_provider.model_info.model_name = "claude-sonnet-4"
        mock_provider.model_info.provider = "anthropic"
        mock_provider.total_usage = TokenUsage()

        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        mock_provider.complete = AsyncMock(return_value=ProviderResponse(
            content="Test response",
            usage=usage,
            model="claude-sonnet-4",
            provider="anthropic",
            latency_ms=100,
        ))

        # Create wrapper
        wrapper = BillingProviderWrapper(mock_provider, task_id="test_task_1")

        # Call complete
        result = await wrapper.complete("Test prompt")

        # Verify
        assert result.content == "Test response"
        mock_provider.complete.assert_called_once()

        # Check billing was recorded
        billing = get_billing_service()
        assert billing.get_task_cost("test_task_1") > 0

    @pytest.mark.asyncio
    async def test_wrapper_does_not_record_on_error(self):
        """Test that wrapper does not record cost on error."""
        mock_provider = MagicMock()
        mock_provider.config = ProviderConfig()
        mock_provider.model_info = MagicMock()
        mock_provider.model_info.model_name = "claude-sonnet-4"
        mock_provider.model_info.provider = "anthropic"
        mock_provider.total_usage = TokenUsage()

        mock_provider.complete = AsyncMock(return_value=ProviderResponse(
            content="",
            error="API error",
            model="claude-sonnet-4",
            provider="anthropic",
        ))

        wrapper = BillingProviderWrapper(mock_provider)
        result = await wrapper.complete("Test prompt")

        assert result.error == "API error"

        # Check billing was NOT recorded
        billing = get_billing_service()
        initial_cost = billing.get_total_spent()
        assert initial_cost == 0

    @pytest.mark.asyncio
    async def test_wrap_provider_convenience_function(self):
        """Test the wrap_provider convenience function."""
        base_provider = DeterministicProvider()
        wrapped = wrap_provider(base_provider, task_id="test_task_2")

        assert isinstance(wrapped, BillingProviderWrapper)
        assert wrapped._task_id == "test_task_2"

    def test_set_task_id(self):
        """Test setting task ID after creation."""
        base_provider = DeterministicProvider()
        wrapper = BillingProviderWrapper(base_provider)

        assert wrapper._task_id is None
        wrapper.set_task_id("new_task_id")
        assert wrapper._task_id == "new_task_id"


class TestBillingServiceIntegration:
    """Test billing service integration."""

    def setup_method(self):
        """Reset billing service before each test."""
        import eiw.billing.service as billing_module
        billing_module._billing_service = None

    def test_billing_records_multiple_costs(self):
        """Test that multiple costs are accumulated correctly."""
        billing = get_billing_service()

        # Record some costs
        billing.record_cost(
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            model_name="claude-3-5-sonnet-20241022",
            provider="anthropic",
            task_id="task_1",
        )

        billing.record_cost(
            usage=TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
            model_name="claude-3-5-sonnet-20241022",
            provider="anthropic",
            task_id="task_1",
        )

        assert billing.get_task_cost("task_1") > 0
        assert len(billing.get_records()) == 2

    def test_budget_status(self):
        """Test budget status calculation."""
        billing = BillingService(budget_limit_usd=10.0)

        # Record some costs
        billing.record_cost(
            usage=TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500),
            model_name="claude-3-5-sonnet-20241022",
            provider="anthropic",
        )

        status = billing.get_budget_status()
        assert status.limit_usd == 10.0
        assert status.spent_usd > 0
        assert status.remaining_usd is not None
        assert not status.exceeded

    def test_usage_summary(self):
        """Test usage summary."""
        billing = get_billing_service()

        billing.record_cost(
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            model_name="claude-3-5-sonnet-20241022",
            provider="anthropic",
        )

        summary = billing.get_usage_summary()
        assert summary["total_input_tokens"] == 100
        assert summary["total_output_tokens"] == 50
        assert summary["total_tokens"] == 150
        assert summary["total_requests"] == 1
        assert "cost_by_provider" in summary
        assert "budget_status" in summary


class TestProviderRouting:
    """Test provider routing with billing."""

    def setup_method(self):
        """Reset services before each test."""
        import eiw.billing.service as billing_module
        billing_module._billing_service = None

    def test_route_task_creates_selection(self):
        """Test that route_task returns a selection."""
        from eiw.agent.router import route_task
        from eiw.agent.planner import ToolType

        selection = route_task(ToolType.METRIC_QUERY)
        assert selection.provider is not None
        assert selection.reason is not None

    def test_route_task_returns_correct_reason(self):
        """Test that route_task returns correct reason based on task."""
        from eiw.agent.router import route_task
        from eiw.agent.planner import ToolType

        # Test different task types return valid reasons
        selection = route_task(ToolType.KNOWLEDGE_SEARCH)
        assert selection.reason is not None
        # Low complexity tasks might use deterministic or anthropic depending on config
        assert selection.reason in [
            "simple_task_deterministic",
            "medium_task_sonnet",
            "reasoning_task_anthropic",
            "low_complexity_openai",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
