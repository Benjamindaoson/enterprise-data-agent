"""Agent Lightning bridge for training against the real Agent Harness."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class AgentLightningConfig:
    openai_base_url: str
    event_url: str = ""
    key: str = ""
    model: str = "auto"
    timeout_seconds: float = 10.0

    @property
    def enabled(self) -> bool:
        return bool(self.openai_base_url)

    @classmethod
    def from_env(cls) -> AgentLightningConfig | None:
        base_url = os.getenv("AGL_OPENAI_BASE_URL", "").strip()
        if not base_url:
            return None
        return cls(
            openai_base_url=base_url,
            event_url=os.getenv("AGL_EVENT_URL", "").strip(),
            key=os.getenv("AGL_KEY", "").strip(),
            model=os.getenv("EIW_AGENT_LIGHTNING_MODEL", "auto").strip() or "auto",
            timeout_seconds=float(
                os.getenv("EIW_AGENT_LIGHTNING_TIMEOUT_SECONDS", "10")
            ),
        )

    def post_event(self, event_type: str, data: dict[str, Any]) -> None:
        if not self.event_url:
            raise RuntimeError("AGL_EVENT_URL is required to emit Agent Lightning events")
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        response = httpx.post(
            self.event_url,
            json={"event_type": event_type, "data": data},
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

    def post_reward(
        self,
        value: float,
        *,
        source: str = "enterprise-data-agent",
        reason: str = "",
    ) -> None:
        bounded = max(0.0, min(1.0, float(value)))
        payload: dict[str, Any] = {"value": bounded, "source": source}
        if reason:
            payload["reason"] = reason[:500]
        self.post_event("reward", payload)


def resolve_model_endpoint(
    explicit_url: str,
    explicit_model: str,
    explicit_api_key: str,
) -> tuple[str, str, str, str]:
    """Let Agent Lightning's rollout proxy override normal model endpoints."""

    config = AgentLightningConfig.from_env()
    if config is not None:
        return (
            config.openai_base_url,
            config.model,
            config.key,
            "agent-lightning",
        )
    return explicit_url, explicit_model, explicit_api_key, "direct"


def compose_reward(
    metrics: dict[str, float],
    *,
    weights: dict[str, float] | None = None,
) -> float:
    if not metrics:
        return 0.0
    selected_weights = weights or {name: 1.0 for name in metrics}
    numerator = 0.0
    denominator = 0.0
    for name, value in metrics.items():
        if name not in selected_weights:
            continue
        weight = float(selected_weights[name])
        if weight <= 0:
            continue
        bounded = max(0.0, min(1.0, float(value)))
        numerator += bounded * weight
        denominator += weight
    return numerator / denominator if denominator else 0.0
