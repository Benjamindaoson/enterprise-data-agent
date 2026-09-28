"""Shared telemetry for model-driven BA Agent decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModelDecisionTelemetry:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    invalid_responses: int = 0
    invalid_choices: int = 0
    replan_calls: int = 0
    fallbacks: int = 0

    def record_call(
        self,
        payload: dict[str, Any],
        *,
        elapsed_ms: float,
        input_cost_per_million: float = 0.0,
        output_cost_per_million: float = 0.0,
    ) -> None:
        self.calls += 1
        self.total_latency_ms += elapsed_ms
        usage = payload.get("usage") or {}
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt + completion))
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += total
        self.estimated_cost_usd += (
            prompt * input_cost_per_million
            + completion * output_cost_per_million
        ) / 1_000_000.0

    def snapshot(self) -> dict[str, float | int]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 8),
            "mean_model_call_latency_ms": (
                self.total_latency_ms / self.calls if self.calls else 0.0
            ),
            "invalid_responses": self.invalid_responses,
            "invalid_choices": self.invalid_choices,
            "replan_calls": self.replan_calls,
            "fallbacks": self.fallbacks,
        }
