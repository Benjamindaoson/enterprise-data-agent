"""Token Billing Service.

Provides:
- Token cost calculation for different providers
- Budget tracking and management
- Cost reporting
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from eiw.agent.provider import TokenUsage
from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "billing")


class ProviderPricing(str, Enum):
    """Provider pricing tiers."""

    # Anthropic Claude pricing (per 1M tokens)
    ANTHROPIC_HAIKU = "anthropic_haiku"  # $0.25 / $1.25
    ANTHROPIC_SONNET = "anthropic_sonnet"  # $3 / $15
    ANTHROPIC_OPUS = "anthropic_opus"  # $15 / $75
    ANTHROPIC_SONNET_4 = "anthropic_sonnet_4"  # $3 / $15

    # OpenAI pricing (per 1M tokens)
    OPENAI_GPT4O = "openai_gpt4o"  # $2.50 / $10
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"  # $0.15 / $0.60
    OPENAI_GPT4_TURBO = "openai_gpt4_turbo"  # $10 / $30

    # Claude pricing (per 1M tokens)
    DEEPSEEK_CHAT = "deepseek_chat"  # $0.14 / $2.19


@dataclass
class ModelPricing:
    """Pricing for a specific model."""

    provider: str
    model_name: str
    input_cost_per_million: float  # USD per 1M input tokens
    output_cost_per_million: float  # USD per 1M output tokens
    currency: str = "USD"


# Model pricing lookup
MODEL_PRICING: dict[str, ModelPricing] = {
    # Anthropic
    "claude-3-haiku-20240307": ModelPricing("anthropic", "claude-3-haiku", 0.25, 1.25),
    "claude-3-5-haiku-20241022": ModelPricing("anthropic", "claude-3-5-haiku", 0.25, 1.25),
    "claude-3-sonnet-20240229": ModelPricing("anthropic", "claude-3-sonnet", 3.0, 15.0),
    "claude-3-5-sonnet-20241022": ModelPricing("anthropic", "claude-3-5-sonnet", 3.0, 15.0),
    "claude-3-opus-20240229": ModelPricing("anthropic", "claude-3-opus", 15.0, 75.0),
    "claude-sonnet-4-20250514": ModelPricing("anthropic", "claude-sonnet-4", 3.0, 15.0),

    # OpenAI
    "gpt-4o": ModelPricing("openai", "gpt-4o", 2.50, 10.0),
    "gpt-4o-mini": ModelPricing("openai", "gpt-4o-mini", 0.15, 0.60),
    "gpt-4-turbo": ModelPricing("openai", "gpt-4-turbo", 10.0, 30.0),
    "gpt-3.5-turbo": ModelPricing("openai", "gpt-3.5-turbo", 0.50, 1.50),

    # DeepSeek
    "deepseek-chat": ModelPricing("deepseek", "deepseek-chat", 0.14, 2.19),
    "deepseek-coder": ModelPricing("deepseek", "deepseek-coder", 0.14, 2.19),
}


@dataclass
class CostRecord:
    """Record of a cost incurred."""

    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetStatus:
    """Current budget status."""

    limit_usd: float | None
    spent_usd: float
    remaining_usd: float | None
    warning_threshold_reached: bool
    exceeded: bool


class BillingService:
    """Service for tracking and calculating token costs."""

    def __init__(self, budget_limit_usd: float | None = None):
        self._budget_limit_usd = budget_limit_usd
        self._records: list[CostRecord] = []
        self._task_costs: dict[str, float] = {}

    def calculate_cost(
        self,
        usage: TokenUsage,
        model_name: str,
    ) -> float:
        """Calculate cost for token usage.

        Args:
            usage: Token usage
            model_name: Model name

        Returns:
            Cost in USD
        """
        # Normalize model name
        model_key = model_name.lower()

        # Look up pricing
        pricing = MODEL_PRICING.get(model_name)
        if not pricing:
            # Try to find by partial match
            for key, p in MODEL_PRICING.items():
                if key in model_key or model_key in key:
                    pricing = p
                    break

        if not pricing:
            # Default to approximate pricing
            logger.warning(f"No pricing found for model {model_name}, using default")
            input_cost = 3.0  # $3 per 1M
            output_cost = 15.0  # $15 per 1M
        else:
            input_cost = pricing.input_cost_per_million
            output_cost = pricing.output_cost_per_million

        # Calculate cost
        input_cost_total = (usage.prompt_tokens / 1_000_000) * input_cost
        output_cost_total = (usage.completion_tokens / 1_000_000) * output_cost

        return round(input_cost_total + output_cost_total, 6)

    def record_cost(
        self,
        usage: TokenUsage,
        model_name: str,
        provider: str,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CostRecord:
        """Record a cost for token usage.

        Args:
            usage: Token usage
            model_name: Model name
            provider: Provider name
            task_id: Optional task ID
            metadata: Optional metadata

        Returns:
            Cost record
        """
        cost = self.calculate_cost(usage, model_name)

        record = CostRecord(
            timestamp=datetime.now(),
            provider=provider,
            model=model_name,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            cost_usd=cost,
            task_id=task_id,
            metadata=metadata or {},
        )

        self._records.append(record)

        if task_id:
            self._task_costs[task_id] = self._task_costs.get(task_id, 0) + cost

        logger.info(
            f"Recorded cost: {cost:.6f} USD",
            extra={
                "task_id": task_id,
                "provider": provider,
                "model": model_name,
                "tokens": usage.total_tokens,
            },
        )

        return record

    def get_total_spent(self) -> float:
        """Get total spent amount."""
        return sum(r.cost_usd for r in self._records)

    def get_budget_status(self, warning_threshold: float = 0.8) -> BudgetStatus:
        """Get current budget status.

        Args:
            warning_threshold: Threshold for warning (0.0-1.0)

        Returns:
            Budget status
        """
        spent = self.get_total_spent()
        remaining = None
        exceeded = False
        warning_reached = False

        if self._budget_limit_usd is not None:
            remaining = self._budget_limit_usd - spent
            exceeded = spent > self._budget_limit_usd
            warning_reached = spent >= (self._budget_limit_usd * warning_threshold)

        return BudgetStatus(
            limit_usd=self._budget_limit_usd,
            spent_usd=spent,
            remaining_usd=remaining,
            warning_threshold_reached=warning_reached,
            exceeded=exceeded,
        )

    def get_task_cost(self, task_id: str) -> float:
        """Get total cost for a task."""
        return self._task_costs.get(task_id, 0.0)

    def get_cost_breakdown(self) -> dict[str, Any]:
        """Get cost breakdown by provider and model."""
        breakdown: dict[str, dict[str, float]] = {}

        for record in self._records:
            if record.provider not in breakdown:
                breakdown[record.provider] = {}
            if record.model not in breakdown[record.provider]:
                breakdown[record.provider][record.model] = 0.0
            breakdown[record.provider][record.model] += record.cost_usd

        return breakdown

    def get_records(self, limit: int = 100) -> list[CostRecord]:
        """Get recent cost records."""
        return self._records[-limit:]

    def get_usage_summary(self) -> dict[str, Any]:
        """Get usage summary with breakdowns."""
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_cost = sum(r.cost_usd for r in self._records)

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 6),
            "total_requests": len(self._records),
            "cost_by_provider": self.get_cost_breakdown(),
            "task_count": len(self._task_costs),
            "budget_status": self.get_budget_status().__dict__,
        }


# Global billing service
_billing_service: BillingService | None = None


def get_billing_service() -> BillingService:
    """Get global billing service."""
    global _billing_service
    if _billing_service is None:
        budget_limit = os.getenv("BUDGET_LIMIT_USD")
        _billing_service = BillingService(
            budget_limit_usd=float(budget_limit) if budget_limit else None
        )
    return _billing_service
