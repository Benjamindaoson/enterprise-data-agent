"""Optional model policies for specialist BA Agents.

Each specialist can choose a bounded set of analytical skills. The model never
executes SQL/Python directly and never emits hidden reasoning; it returns only
an allowlisted skill plan plus a short public rationale. Deterministic skill
selection remains the default and fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from eiw.retail.model_client import ChatClient, OpenAICompatibleChatClient, PolicyTelemetry
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
    client: ChatClient | None = None
    telemetry: PolicyTelemetry | None = None

    def decide(
        self,
        *,
        workstream: WorkstreamName,
        question: str,
        allowed_skills: tuple[str, ...],
    ) -> SpecialistDecision:
        payload = {
            "workstream": workstream.value,
            "question": question,
            "allowed_skills": list(allowed_skills),
            "contract": (
                "Return JSON only with skills and rationale. Select only from "
                "allowed_skills. rationale is public and short."
            ),
        }
        if self.telemetry is not None:
            self.telemetry.record_call()
        client = self.client or OpenAICompatibleChatClient(
            base_url=self.base_url,
            model=self.model,
            api_key=self.api_key,
            timeout_seconds=self.timeout_seconds,
        )
        try:
            raw = client.complete(
                system=(
                    "You are a specialist business-analysis agent. Choose only "
                    "the supplied analytical skills. Return bounded JSON; do not "
                    "reveal chain-of-thought."
                ),
                user=json.dumps(payload, ensure_ascii=False),
            ).content
            value = self._parse_json(raw)
            raw_skills = value.get("skills", [])
            if not isinstance(raw_skills, list):
                raise ValueError("Specialist skills must be a list")
            allowed = set(allowed_skills)
            invalid = 0
            skills: list[str] = []
            for raw_skill in raw_skills:
                skill = str(raw_skill)
                if skill not in allowed:
                    invalid += 1
                    continue
                if skill not in skills:
                    skills.append(skill)
            if self.telemetry is not None:
                self.telemetry.record_invalid(invalid)
            if not skills:
                skills = list(allowed_skills)
            return SpecialistDecision(
                skills=skills,
                rationale=str(value.get("rationale", ""))[:500],
            )
        except Exception:
            if self.telemetry is not None:
                self.telemetry.record_failure()
            raise

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
