"""Budget-aware model routing for business-agent steps."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ModelTier(StrEnum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    REASONING = "REASONING"


@dataclass(frozen=True, slots=True)
class ModelRoute:
    tier: ModelTier
    model: str
    max_output_tokens: int
    rationale: str


class ModelRouter:
    def __init__(
        self,
        *,
        fast_model: str = "Qwen/Qwen3-0.6B",
        standard_model: str = "Qwen/Qwen3-4B-Instruct-2507",
        reasoning_model: str = "Qwen/Qwen3-32B",
    ) -> None:
        self.fast_model = fast_model
        self.standard_model = standard_model
        self.reasoning_model = reasoning_model

    def route(
        self,
        *,
        complexity: float,
        risk: float,
        remaining_tokens: int,
        verification: bool = False,
    ) -> ModelRoute:
        if remaining_tokens < 1200 and not verification:
            return ModelRoute(ModelTier.FAST, self.fast_model, 256, "token budget is constrained")
        score = max(complexity, risk)
        if verification or score >= 0.8:
            return ModelRoute(
                ModelTier.REASONING,
                self.reasoning_model,
                min(2048, max(512, remaining_tokens // 2)),
                "high-risk/complex step requires stronger reasoning",
            )
        if score >= 0.4:
            return ModelRoute(
                ModelTier.STANDARD,
                self.standard_model,
                min(1024, max(384, remaining_tokens // 3)),
                "moderate-complexity business reasoning",
            )
        return ModelRoute(ModelTier.FAST, self.fast_model, 384, "simple bounded action selection")
