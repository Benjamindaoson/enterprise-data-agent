"""Provider-neutral token and dollar cost accounting."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


@dataclass(slots=True)
class CostLedger:
    prices: dict[str, ModelPrice] = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    dollar_cost: float = 0.0
    calls: int = 0

    def record(self, model: str, *, input_tokens: int, output_tokens: int) -> float:
        price = self.prices.get(model)
        if price is None:
            raise KeyError(f"no configured price for model: {model}")
        cost = (
            input_tokens / 1_000_000 * price.input_per_million
            + output_tokens / 1_000_000 * price.output_per_million
        )
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.dollar_cost += cost
        self.calls += 1
        return cost

    def snapshot(self) -> dict[str, float | int]:
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "dollar_cost": round(self.dollar_cost, 8),
        }
