"""Optional model policies for specialist BA Agents."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from eiw.retail.model_telemetry import ModelDecisionTelemetry
from eiw.retail.models import WorkstreamName

SPECIALIST_SKILLS: dict[WorkstreamName, tuple[str, ...]] = {
    WorkstreamName.OVERVIEW: ("kpi_overview",),
    WorkstreamName.STORE: (
        "store_contribution",
        "store_anomaly",
        "store_commodity_scan",
    ),
    WorkstreamName.PRODUCT: (
        "commodity_contribution",
        "price_volume",
    ),
    WorkstreamName.PROMOTION: ("merchandising",),
    WorkstreamName.CUSTOMER: (
        "customer_segments",
        "basket_affinity",
        "income_segments",
        "household_composition",
        "coupon_funnel",
    ),
}


class SpecialistDecision(BaseModel):
    skills: list[str] = Field(default_factory=list)
    rationale: str = Field(default="", max_length=500)


class SpecialistPolicy(Protocol):
    def decide(
        self,
        *,
        workstream: WorkstreamName,
        question: str,
        allowed_skills: tuple[str, ...],
    ) -> SpecialistDecision: ...


@dataclass
class OpenAICompatibleSpecialistPolicy:
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
        workstream: WorkstreamName,
        question: str,
        allowed_skills: tuple[str, ...],
    ) -> SpecialistDecision:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request_payload = {
            "workstream": workstream.value,
            "question": question,
            "allowed_skills": list(allowed_skills),
            "contract": (
                "Return JSON only with skills and rationale. Select only from "
                "allowed_skills. rationale is public and short."
            ),
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
                                "You are a specialist business-analysis agent. "
                                "Choose only the supplied analytical skills. "
                                "Do not reveal chain-of-thought."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(request_payload, ensure_ascii=False),
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
            value = self._parse_json(raw)
            decision = SpecialistDecision.model_validate(value)
        except Exception:
            if self.telemetry.calls == 0 or self.telemetry.total_latency_ms == 0.0:
                self.telemetry.record_call(
                    {},
                    elapsed_ms=(perf_counter() - started) * 1000.0,
                )
            self.telemetry.invalid_responses += 1
            self.telemetry.fallbacks += 1
            raise

        allowed = set(allowed_skills)
        invalid = [skill for skill in decision.skills if skill not in allowed]
        self.telemetry.invalid_choices += len(invalid)
        skills: list[str] = []
        for skill in decision.skills:
            if skill in allowed and skill not in skills:
                skills.append(skill)
        if not skills:
            skills = list(allowed_skills)
        return decision.model_copy(update={"skills": skills})

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Specialist policy did not return a JSON object")
        value = json.loads(raw[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("Specialist decision must be a JSON object")
        return value


def deterministic_specialist_decision(
    workstream: WorkstreamName,
) -> SpecialistDecision:
    return SpecialistDecision(
        skills=list(SPECIALIST_SKILLS[workstream]),
        rationale="Deterministic specialist policy selected the full verified skill set.",
    )
