"""Architecture benchmark for deterministic and model-driven Retail BA lanes."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from eiw.retail.benchmark import RetailBenchmarkCase, RetailBenchmarkRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.model_client import ChatClient, PolicyTelemetry
from eiw.retail.runtime import RetailBARuntime
from eiw.retail.specialist_policy import OpenAICompatibleSpecialistPolicy
from eiw.retail.supervisor import (
    OpenAICompatibleSupervisor,
    SupervisorDecision,
    SupervisorPolicy,
)


class ArchitectureMode(StrEnum):
    DETERMINISTIC = "deterministic"
    SINGLE_AGENT = "single-agent"
    SUPERVISOR = "supervisor"
    SUPERVISOR_SPECIALISTS = "supervisor+specialists"


class OneShotSupervisor:
    """Single-agent baseline: one model planning decision, no model replan wave."""

    def __init__(self, delegate: SupervisorPolicy) -> None:
        self.delegate = delegate

    def decide(
        self,
        *,
        stage: str,
        question: str,
        completed: list[Any],
        max_workstreams: int,
    ) -> SupervisorDecision:
        if stage == "replan":
            return SupervisorDecision(
                workstreams=[],
                rationale="Single-agent baseline uses one upfront model plan.",
            )
        return self.delegate.decide(
            stage=stage,
            question=question,
            completed=completed,
            max_workstreams=max_workstreams,
        )


class ModelArchitectureBenchmark:
    """Compare architecture choices while holding data, cases and skills fixed."""

    def __init__(
        self,
        data: RetailDataEngine,
        *,
        provider: str,
        model: str,
        client_factory: Callable[[], ChatClient],
    ) -> None:
        self.data = data
        self.provider = provider
        self.model = model
        self.client_factory = client_factory

    def run(
        self,
        *,
        case_limit: int = 10,
        modes: tuple[ArchitectureMode, ...] = tuple(ArchitectureMode),
    ) -> dict[str, object]:
        baseline_runner = RetailBenchmarkRunner(RetailBARuntime(self.data))
        suite = baseline_runner.build_cases()[:case_limit]
        rows = [self._run_mode(mode, suite) for mode in modes]
        return {
            "suite": "RetailModelArchitectureBench-v1",
            "provider": self.provider,
            "model": self.model,
            "cases_per_architecture": len(suite),
            "architectures": rows,
            "definitions": {
                "deterministic": "deterministic supervisor and deterministic specialist skills",
                "single-agent": "one upfront model planner; deterministic specialist skills; no model replan",
                "supervisor": "model supervisor with replan; deterministic specialist skills",
                "supervisor+specialists": "model supervisor plus model-selected bounded skills per specialist",
                "success": (
                    "case passes driver recall >=0.80, semantic coverage >=0.90, "
                    "numeric accuracy=1, report completeness=1, and action present"
                ),
            },
        }

    def _run_mode(
        self,
        mode: ArchitectureMode,
        suite: tuple[RetailBenchmarkCase, ...],
    ) -> dict[str, object]:
        client: ChatClient | None = None
        supervisor_telemetry: PolicyTelemetry | None = None
        specialist_telemetry: PolicyTelemetry | None = None

        if mode == ArchitectureMode.DETERMINISTIC:
            runtime = RetailBARuntime(self.data)
        else:
            client = self.client_factory()
            supervisor_telemetry = PolicyTelemetry()
            supervisor = OpenAICompatibleSupervisor(
                base_url="instrumented://provider",
                model=self.model,
                client=client,
                telemetry=supervisor_telemetry,
            )
            supervisor_policy: SupervisorPolicy = supervisor
            if mode == ArchitectureMode.SINGLE_AGENT:
                supervisor_policy = OneShotSupervisor(supervisor)

            specialist_policy = None
            if mode == ArchitectureMode.SUPERVISOR_SPECIALISTS:
                specialist_telemetry = PolicyTelemetry()
                specialist_policy = OpenAICompatibleSpecialistPolicy(
                    base_url="instrumented://provider",
                    model=self.model,
                    client=client,
                    telemetry=specialist_telemetry,
                )
            runtime = RetailBARuntime(
                self.data,
                supervisor_policy=supervisor_policy,
                specialist_policy=specialist_policy,
            )

        quality = RetailBenchmarkRunner(runtime).run(suite)
        result_rows = quality["results"]
        assert isinstance(result_rows, list)
        passed = sum(self._case_success(row) for row in result_rows)
        calls = 0
        failures = 0
        invalid_items = 0
        telemetry_rows = [
            item.snapshot()
            for item in (supervisor_telemetry, specialist_telemetry)
            if item is not None
        ]
        for row in telemetry_rows:
            calls += int(row["calls"])
            failures += int(row["failures"])
            invalid_items += int(row["invalid_items"])

        usage: dict[str, int | float] = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
            "model_latency_ms": 0.0,
        }
        if client is not None:
            usage = client.ledger.snapshot()

        return {
            "architecture": mode.value,
            "success_rate": round(passed / max(1, len(result_rows)), 4),
            "driver_recall_at_k": quality["driver_recall_at_k"],
            "semantic_coverage": quality["semantic_coverage"],
            "numeric_accuracy": quality["numeric_accuracy"],
            "report_completeness": quality["report_completeness"],
            "action_coverage": quality["action_coverage"],
            "mean_latency_ms": quality["mean_elapsed_ms"],
            "p95_latency_ms": quality["p95_elapsed_ms"],
            "replan_rate": quality["replan_rate"],
            "model_calls": int(usage["calls"]),
            "prompt_tokens": int(usage["prompt_tokens"]),
            "completion_tokens": int(usage["completion_tokens"]),
            "cost_usd": float(usage["cost_usd"]),
            "model_latency_ms": float(usage["model_latency_ms"]),
            "invalid_decisions": invalid_items,
            "invalid_decision_rate": round(
                invalid_items / calls if calls else 0.0,
                4,
            ),
            "fallback_rate": round(
                failures / calls if calls else 0.0,
                4,
            ),
        }

    @staticmethod
    def _case_success(row: object) -> bool:
        if not isinstance(row, dict):
            return False
        return (
            float(row.get("driver_recall_at_k", 0.0)) >= 0.80
            and float(row.get("semantic_coverage", 0.0)) >= 0.90
            and float(row.get("numeric_accuracy", 0.0)) >= 1.0
            and float(row.get("report_completeness", 0.0)) >= 1.0
            and float(row.get("has_action", 0.0)) >= 1.0
        )
