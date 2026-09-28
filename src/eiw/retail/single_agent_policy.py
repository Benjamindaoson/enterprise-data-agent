"""Single model policy that chooses all workstreams and skills in one call."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter

import httpx
from pydantic import BaseModel, Field

from eiw.retail.model_telemetry import ModelDecisionTelemetry
from eiw.retail.models import WorkstreamName, WorkstreamResult
from eiw.retail.specialist_policy import SPECIALIST_SKILLS, SpecialistDecision
from eiw.retail.supervisor import SupervisorDecision


class SingleAgentPlan(BaseModel):
    workstreams: list[WorkstreamName] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    rationale: str = Field(default="", max_length=500)


@dataclass
class OpenAICompatibleSingleAgentPolicy:
    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 60.0
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0
    telemetry: ModelDecisionTelemetry = field(default_factory=ModelDecisionTelemetry)
    _cache: dict[str, SingleAgentPlan] = field(default_factory=dict, init=False)

    def decide(
        self,
        *,
        stage: str | None = None,
        question: str,
        completed: list[WorkstreamResult] | None = None,
        max_workstreams: int | None = None,
        workstream: WorkstreamName | None = None,
        allowed_skills: tuple[str, ...] | None = None,
    ) -> SupervisorDecision | SpecialistDecision:
        if workstream is not None:
            plan = self._plan(question)
            allowed = set(allowed_skills or ())
            proposed = plan.skills.get(workstream.value, [])
            invalid = [skill for skill in proposed if skill not in allowed]
            self.telemetry.invalid_choices += len(invalid)
            selected = [skill for skill in proposed if skill in allowed]
            if not selected:
                selected = list(allowed_skills or ())
            return SpecialistDecision(skills=selected, rationale=plan.rationale)

        if stage == "replan":
            # A true single-agent lane plans once and does not make a second model call.
            return SupervisorDecision(
                workstreams=[],
                rationale="Single-agent lane uses one initial global plan.",
            )

        plan = self._plan(question)
        limit = max_workstreams or len(plan.workstreams)
        return SupervisorDecision(
            workstreams=plan.workstreams[:limit],
            rationale=plan.rationale,
        )

    def _plan(self, question: str) -> SingleAgentPlan:
        cached = self._cache.get(question)
        if cached is not None:
            return cached

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        contract = {
            "question": question,
            "allowed_workstreams": [item.value for item in WorkstreamName],
            "allowed_skills": {
                name.value: list(skills)
                for name, skills in SPECIALIST_SKILLS.items()
            },
            "response_contract": {
                "workstreams": ["store", "product"],
                "skills": {"store": ["store_contribution"]},
                "rationale": "short public rationale",
            },
        }
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
                                "Plan one bounded retail business analysis. Return JSON "
                                "only. Use only allowed workstreams and skills."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(contract, ensure_ascii=False),
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
            raw = str(payload["choices"][0]["message"]["content"])
            start = raw.find("{")
            end = raw.rfind("}")
            if start < 0 or end < start:
                raise ValueError("single-agent model did not return JSON")
            value = json.loads(raw[start : end + 1])
            plan = SingleAgentPlan.model_validate(value)
        except Exception:
            if self.telemetry.calls == 0 or self.telemetry.total_latency_ms == 0.0:
                self.telemetry.record_call(
                    {},
                    elapsed_ms=(perf_counter() - started) * 1000.0,
                )
            self.telemetry.invalid_responses += 1
            self.telemetry.fallbacks += 1
            raise

        deduped: list[WorkstreamName] = []
        for item in plan.workstreams:
            if item not in deduped:
                deduped.append(item)
        plan = plan.model_copy(update={"workstreams": deduped})
        self._cache[question] = plan
        return plan
