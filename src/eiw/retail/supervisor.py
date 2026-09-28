"""Optional model-driven Supervisor policy for retail multi-agent orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from eiw.retail.model_telemetry import ModelDecisionTelemetry
from eiw.retail.models import WorkstreamName, WorkstreamResult


class SupervisorDecision(BaseModel):
    workstreams: list[WorkstreamName] = Field(default_factory=list)
    rationale: str = Field(default="", max_length=500)


class SupervisorPolicy(Protocol):
    def decide(
        self,
        *,
        stage: str,
        question: str,
        completed: list[WorkstreamResult],
        max_workstreams: int,
    ) -> SupervisorDecision: ...


@dataclass
class OpenAICompatibleSupervisor:
    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 60.0
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0
    telemetry: ModelDecisionTelemetry = field(default_factory=ModelDecisionTelemetry)

    def decide(
        self,
        *,
        stage: str,
        question: str,
        completed: list[WorkstreamResult],
        max_workstreams: int,
    ) -> SupervisorDecision:
        if stage == "replan":
            self.telemetry.replan_calls += 1
        summaries = [
            {
                "workstream": item.name.value,
                "summary": item.summary,
                "metrics": item.metrics,
            }
            for item in completed
        ]
        allowed = [item.value for item in WorkstreamName]
        prompt = {
            "task": (
                "Choose the next business-analysis workstreams. Return only a "
                "JSON object with keys workstreams and rationale."
            ),
            "stage": stage,
            "question": question,
            "allowed_workstreams": allowed,
            "completed": summaries,
            "constraints": {
                "max_workstreams": max_workstreams,
                "do_not_repeat_completed": stage == "replan",
                "rationale": "one short public explanation, no hidden reasoning",
            },
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        started = perf_counter()
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a BA Agent supervisor. Select only from the "
                                "provided workstream allowlist. Do not reveal chain-of-thought."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(prompt, ensure_ascii=False),
                        },
                    ],
                    "temperature": 0.0,
                    "stream": False,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            self.telemetry.record_call(
                payload,
                elapsed_ms=(perf_counter() - started) * 1000.0,
                input_cost_per_million=self.input_cost_per_million,
                output_cost_per_million=self.output_cost_per_million,
            )
            raw = str(payload["choices"][0]["message"]["content"]).strip()
            parsed = self._parse_json(raw)
            decision = SupervisorDecision.model_validate(parsed)
        except Exception:
            if self.telemetry.calls == 0 or self.telemetry.total_latency_ms == 0.0:
                self.telemetry.record_call(
                    {},
                    elapsed_ms=(perf_counter() - started) * 1000.0,
                )
            self.telemetry.invalid_responses += 1
            self.telemetry.fallbacks += 1
            raise

        completed_names = {item.name for item in completed}
        deduped: list[WorkstreamName] = []
        for name in decision.workstreams:
            if stage == "replan" and name in completed_names:
                self.telemetry.invalid_choices += 1
                continue
            if name not in deduped:
                deduped.append(name)
        return decision.model_copy(update={"workstreams": deduped[:max_workstreams]})

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        fence = chr(96) * 3
        if raw.startswith(fence):
            raw = raw.strip(chr(96))
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:].lstrip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Supervisor model did not return a JSON object")
        value = json.loads(raw[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("Supervisor decision must be a JSON object")
        return value
