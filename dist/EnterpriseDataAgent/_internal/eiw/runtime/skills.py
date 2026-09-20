"""Typed skill registry used by the business agent runtime."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    skill_id: str
    description: str
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    tool_dependencies: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    version: str = "1.0.0"


@dataclass(slots=True)
class SkillRegistry:
    _skills: dict[str, SkillDefinition] = field(default_factory=dict)

    def register(self, skill: SkillDefinition) -> None:
        existing = self._skills.get(skill.skill_id)
        if existing is not None and existing.version == skill.version:
            raise ValueError(f"skill already registered: {skill.skill_id}@{skill.version}")
        self._skills[skill.skill_id] = skill

    def get(self, skill_id: str) -> SkillDefinition:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise KeyError(f"unknown skill: {skill_id}") from exc

    def search(self, tags: Iterable[str]) -> list[SkillDefinition]:
        wanted = {tag.lower() for tag in tags}
        if not wanted:
            return list(self._skills.values())
        return [
            skill
            for skill in self._skills.values()
            if wanted.intersection(tag.lower() for tag in skill.tags)
        ]

    def list(self) -> list[SkillDefinition]:
        return sorted(self._skills.values(), key=lambda skill: skill.skill_id)


def default_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for skill in (
        SkillDefinition(
            skill_id="business.metric_analysis",
            description="Resolve governed metrics and compare business performance.",
            input_schema={"question": "str"},
            output_schema={"findings": "list", "evidence": "list"},
            tool_dependencies=("semantic_layer", "metric_query", "verification"),
            permissions=("analytics:read",),
            tags=("analytics", "bi", "metrics"),
        ),
        SkillDefinition(
            skill_id="business.attribution",
            description="Drill down across dimensions and rank observed contributors.",
            input_schema={"metric": "str", "dimensions": "list[str]"},
            output_schema={"contributors": "list", "limitations": "list"},
            tool_dependencies=("contribution_analysis", "python_sandbox", "verification"),
            permissions=("analytics:read",),
            tags=("analytics", "attribution", "root-cause"),
        ),
        SkillDefinition(
            skill_id="business.marketing_budget",
            description="Create a constrained marketing-budget allocation proposal.",
            input_schema={"budget": "number", "segments": "list"},
            output_schema={"allocation": "list", "expected_metrics": "dict"},
            tool_dependencies=("campaign_history", "optimizer", "campaign_api"),
            permissions=("marketing:read", "marketing:propose"),
            tags=("marketing", "budget", "operations"),
        ),
        SkillDefinition(
            skill_id="business.sales_expansion",
            description="Prioritize merchant or account opportunities for sales outreach.",
            input_schema={"market": "str", "capacity": "int"},
            output_schema={"leads": "list", "evidence": "list"},
            tool_dependencies=("merchant_profile", "opportunity_ranker", "crm"),
            permissions=("sales:read", "crm:propose"),
            tags=("sales", "merchant", "operations"),
        ),
        SkillDefinition(
            skill_id="business.monetization",
            description="Identify monetization opportunities and propose product matches.",
            input_schema={"merchant_scope": "list"},
            output_schema={"opportunities": "list", "revenue_estimate": "dict"},
            tool_dependencies=("merchant_profile", "product_catalog", "revenue_simulator"),
            permissions=("monetization:read", "monetization:propose"),
            tags=("monetization", "merchant", "operations"),
        ),
        SkillDefinition(
            skill_id="runtime.verify_action",
            description="Verify evidence, permissions, budgets and approval before execution.",
            input_schema={"action": "object"},
            output_schema={"allowed": "bool", "reasons": "list"},
            tool_dependencies=("policy_engine", "audit_log"),
            permissions=("runtime:verify",),
            tags=("safety", "verification", "runtime"),
        ),
    ):
        registry.register(skill)
    return registry
