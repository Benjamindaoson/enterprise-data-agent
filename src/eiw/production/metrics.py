"""OpenTelemetry metrics for the production Agent runtime."""

from __future__ import annotations

from typing import Any

from opentelemetry import metrics


class RuntimeMetrics:
    def __init__(self) -> None:
        meter = metrics.get_meter("eiw.business_agent")
        self.task_counter = meter.create_counter("eiw.agent.tasks")
        self.tool_counter = meter.create_counter("eiw.agent.tool_calls")
        self.policy_violation_counter = meter.create_counter("eiw.agent.policy_violations")
        self.token_counter = meter.create_counter("eiw.agent.tokens")
        self.cost_histogram = meter.create_histogram("eiw.agent.cost_usd")
        self.latency_histogram = meter.create_histogram("eiw.agent.step_latency_ms")

    def record_task(self, *, success: bool, scenario: str) -> None:
        self.task_counter.add(1, {"success": str(success).lower(), "scenario": scenario})

    def record_tool(self, *, tool: str, success: bool) -> None:
        self.tool_counter.add(1, {"tool": tool, "success": str(success).lower()})

    def record_policy_violation(self, *, category: str) -> None:
        self.policy_violation_counter.add(1, {"category": category})

    def record_usage(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        base = {"model": model, **(attributes or {})}
        self.token_counter.add(input_tokens, {**base, "direction": "input"})
        self.token_counter.add(output_tokens, {**base, "direction": "output"})
        self.cost_histogram.record(cost_usd, base)
        self.latency_histogram.record(latency_ms, base)
