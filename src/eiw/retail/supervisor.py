"""Optional model-driven Supervisor policy for retail multi-agent orchestration.

The default BA Agent remains deterministic and reproducible. When configured,
this adapter lets an OpenAI-compatible model choose the public workstream plan
and re-plan after seeing typed intermediate summaries. It never receives or
returns hidden chain-of-thought; only bounded workstream decisions and a short
public rationale are accepted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from eiw.retail.model_client import ChatClient, OpenAICompatibleChatClient, PolicyTelemetry
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
    client: ChatClient | None = None
    telemetry: PolicyTelemetry | None = None

    def decide(
        self,
        *,
        stage: str,
        question: str,
        completed: list[WorkstreamResult],
        max_workstreams: int,
    ) -> SupervisorDecision:
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
        if self.telemetry is not None:
            self.telemetry.record_call(stage=stage)
        client = self.client or OpenAICompatibleChatClient(
            base_url=self.base_url,
            model=self.model,
            api_key=self.api_key,
            timeout_seconds=self.timeout_seconds,
        )
        try:
            raw = client.complete(
                system=(
                    "You are a BA Agent supervisor. Select only from the provided "
                    "workstream allowlist. Return bounded JSON; do not reveal "
                    "chain-of-thought."
                ),
                user=json.dumps(prompt, ensure_ascii=False),
            ).content.strip()
            parsed = self._parse_json(raw)
            raw_workstreams = parsed.get("workstreams", [])
            if not isinstance(raw_workstreams, list):
                raise ValueError("Supervisor workstreams must be a list")

            invalid = 0
            selected: list[WorkstreamName] = []
            for raw_name in raw_workstreams:
                try:
                    name = WorkstreamName(str(raw_name))
                except ValueError:
                    invalid += 1
                    continue
                if name not in selected:
                    selected.append(name)
            if self.telemetry is not None:
                self.telemetry.record_invalid(invalid)

            completed_names = {item.name for item in completed}
            deduped = [
                name
                for name in selected
                if not (stage == "replan" and name in completed_names)
            ][:max_workstreams]
            if self.telemetry is not None and stage == "replan":
                self.telemetry.record_replan_result(nonempty=bool(deduped))
            return SupervisorDecision(
                workstreams=deduped,
                rationale=str(parsed.get("rationale", ""))[:500],
            )
        except Exception:
            if self.telemetry is not None:
                self.telemetry.record_failure()
            raise

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
