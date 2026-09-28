"""Comparative benchmark for deterministic and model-driven retail Agent lanes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from eiw.retail.benchmark import RetailBenchmarkCase, RetailBenchmarkRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime
from eiw.retail.single_agent_policy import OpenAICompatibleSingleAgentPolicy
from eiw.retail.specialist_policy import OpenAICompatibleSpecialistPolicy
from eiw.retail.supervisor import OpenAICompatibleSupervisor


@dataclass(frozen=True)
class ModelProviderSpec:
    name: str
    base_url: str
    model: str
    api_key: str
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0

    @classmethod
    def from_env(cls, name: str) -> "ModelProviderSpec | None":
        prefix = f"EIW_BENCH_{name.upper()}"
        base_url = os.getenv(f"{prefix}_BASE_URL", "").strip()
        model = os.getenv(f"{prefix}_MODEL", "").strip()
        api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
        if not base_url or not model:
            return None
        return cls(
            name=name,
            base_url=base_url,
            model=model,
            api_key=api_key,
            input_cost_per_million=float(
                os.getenv(f"{prefix}_INPUT_COST_PER_MILLION", "0") or 0
            ),
            output_cost_per_million=float(
                os.getenv(f"{prefix}_OUTPUT_COST_PER_MILLION", "0") or 0
            ),
        )


class RetailModelLaneBenchmark:
    def __init__(self, data: RetailDataEngine) -> None:
        self.data = data

    @staticmethod
    def _success_rate(result: dict[str, Any]) -> float:
        rows = result["results"]
        passed = 0
        for row in rows:
            ok = (
                float(row["driver_recall_at_k"]) >= 0.8
                and float(row["semantic_coverage"]) >= 0.95
                and float(row["numeric_accuracy"]) == 1.0
                and float(row["report_completeness"]) >= 0.75
                and float(row["has_action"]) == 1.0
            )
            passed += int(ok)
        return passed / len(rows) if rows else 0.0

    @staticmethod
    def _telemetry(*items: object) -> dict[str, float | int]:
        snapshots = [
            item.telemetry.snapshot()  # type: ignore[attr-defined]
            for item in items
            if item is not None
        ]
        calls = sum(int(row["calls"]) for row in snapshots)
        invalid = sum(
            int(row["invalid_responses"]) + int(row["invalid_choices"])
            for row in snapshots
        )
        return {
            "model_calls": calls,
            "prompt_tokens": sum(int(row["prompt_tokens"]) for row in snapshots),
            "completion_tokens": sum(
                int(row["completion_tokens"]) for row in snapshots
            ),
            "total_tokens": sum(int(row["total_tokens"]) for row in snapshots),
            "estimated_cost_usd": round(
                sum(float(row["estimated_cost_usd"]) for row in snapshots),
                8,
            ),
            "invalid_tool_rate": min(1.0, invalid / calls) if calls else 0.0,
            "fallbacks": sum(int(row["fallbacks"]) for row in snapshots),
        }

    def _result_row(
        self,
        *,
        provider: str,
        model: str,
        lane: str,
        benchmark: dict[str, Any],
        telemetry: dict[str, float | int],
    ) -> dict[str, Any]:
        return {
            "provider": provider,
            "model": model,
            "lane": lane,
            "success": self._success_rate(benchmark),
            "cost_usd": telemetry["estimated_cost_usd"],
            "latency_ms": benchmark["mean_elapsed_ms"],
            "invalid_tool_rate": telemetry["invalid_tool_rate"],
            "replan_rate": benchmark.get("replan_rate", 0.0),
            "model_calls": telemetry["model_calls"],
            "total_tokens": telemetry["total_tokens"],
            "fallbacks": telemetry["fallbacks"],
        }

    def run(
        self,
        providers: list[ModelProviderSpec],
        *,
        cases: tuple[RetailBenchmarkCase, ...] | None = None,
    ) -> dict[str, Any]:
        base_runtime = RetailBARuntime(self.data)
        suite = cases or RetailBenchmarkRunner(base_runtime).build_cases()

        deterministic = RetailBenchmarkRunner(base_runtime).run(suite)
        rows = [
            self._result_row(
                provider="deterministic",
                model="none",
                lane="deterministic",
                benchmark=deterministic,
                telemetry={
                    "estimated_cost_usd": 0.0,
                    "invalid_tool_rate": 0.0,
                    "model_calls": 0,
                    "total_tokens": 0,
                    "fallbacks": 0,
                },
            )
        ]

        for provider in providers:
            common = {
                "base_url": provider.base_url,
                "model": provider.model,
                "api_key": provider.api_key,
                "input_cost_per_million": provider.input_cost_per_million,
                "output_cost_per_million": provider.output_cost_per_million,
            }

            single = OpenAICompatibleSingleAgentPolicy(**common)
            single_runtime = RetailBARuntime(
                self.data,
                supervisor_policy=single,  # type: ignore[arg-type]
                specialist_policy=single,  # type: ignore[arg-type]
            )
            single_result = RetailBenchmarkRunner(single_runtime).run(suite)
            rows.append(
                self._result_row(
                    provider=provider.name,
                    model=provider.model,
                    lane="single-agent",
                    benchmark=single_result,
                    telemetry=self._telemetry(single),
                )
            )

            supervisor = OpenAICompatibleSupervisor(**common)
            supervisor_runtime = RetailBARuntime(
                self.data,
                supervisor_policy=supervisor,
            )
            supervisor_result = RetailBenchmarkRunner(supervisor_runtime).run(suite)
            rows.append(
                self._result_row(
                    provider=provider.name,
                    model=provider.model,
                    lane="supervisor",
                    benchmark=supervisor_result,
                    telemetry=self._telemetry(supervisor),
                )
            )

            full_supervisor = OpenAICompatibleSupervisor(**common)
            specialist = OpenAICompatibleSpecialistPolicy(**common)
            full_runtime = RetailBARuntime(
                self.data,
                supervisor_policy=full_supervisor,
                specialist_policy=specialist,
            )
            full_result = RetailBenchmarkRunner(full_runtime).run(suite)
            rows.append(
                self._result_row(
                    provider=provider.name,
                    model=provider.model,
                    lane="supervisor+specialists",
                    benchmark=full_result,
                    telemetry=self._telemetry(full_supervisor, specialist),
                )
            )

        return {
            "suite": "RetailModelLaneBench-v1",
            "cases": len(suite),
            "providers": [provider.name for provider in providers],
            "live_model_results": bool(providers),
            "rows": rows,
        }
