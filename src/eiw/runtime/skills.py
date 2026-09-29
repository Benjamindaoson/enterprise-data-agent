"""Versioned Skill representation, organization and scheduling for the Agent runtime."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from enum import StrEnum


class SkillLifecycle(StrEnum):
    ACTIVE = "active"
    CANDIDATE = "candidate"
    RETIRED = "retired"


class SkillRisk(StrEnum):
    READ_ONLY = "read_only"
    CODE_EXECUTION = "code_execution"
    REVERSIBLE_WRITE = "reversible_write"
    FINANCIAL_COMMITMENT = "financial_commitment"


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
    workstreams: tuple[str, ...] = ()
    intents: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    implementation_ref: str = ""
    risk: SkillRisk = SkillRisk.READ_ONLY
    lifecycle: SkillLifecycle = SkillLifecycle.ACTIVE
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    parent_version: str | None = None
    evidence_refs: tuple[str, ...] = ()

    @property
    def ref(self) -> str:
        return f"{self.skill_id}@{self.version}"


@dataclass(frozen=True, slots=True)
class SkillCollection:
    collection_id: str
    description: str
    skill_ids: tuple[str, ...]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillScheduleRequest:
    question: str
    workstream: str | None = None
    intents: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    permissions: tuple[str, ...] | None = None
    max_skills: int = 8
    max_estimated_cost: float | None = None
    max_estimated_latency_ms: float | None = None
    allow_code_execution: bool = True


@dataclass(frozen=True, slots=True)
class ScheduledSkill:
    skill_id: str
    version: str
    score: float
    reason: str


@dataclass(frozen=True, slots=True)
class SkillSchedule:
    skills: tuple[ScheduledSkill, ...]
    estimated_cost: float
    estimated_latency_ms: float

    @property
    def skill_ids(self) -> tuple[str, ...]:
        return tuple(item.skill_id for item in self.skills)


@dataclass(slots=True)
class SkillRegistry:
    """Versioned Skill registry with explicit staging and promotion semantics."""

    _skills: dict[str, SkillDefinition] = field(default_factory=dict)
    _versions: dict[str, dict[str, SkillDefinition]] = field(default_factory=dict)
    _collections: dict[str, SkillCollection] = field(default_factory=dict)

    def register(self, skill: SkillDefinition, *, make_current: bool = True) -> None:
        versions = self._versions.setdefault(skill.skill_id, {})
        if skill.version in versions:
            raise ValueError(f"skill already registered: {skill.ref}")
        versions[skill.version] = skill
        if make_current:
            active = replace(skill, lifecycle=SkillLifecycle.ACTIVE)
            versions[skill.version] = active
            self._skills[skill.skill_id] = active

    def stage(self, skill: SkillDefinition) -> None:
        self.register(replace(skill, lifecycle=SkillLifecycle.CANDIDATE), make_current=False)

    def promote(
        self,
        skill_id: str,
        version: str,
        *,
        expected_parent_version: str | None = None,
    ) -> SkillDefinition:
        candidate = self.get(skill_id, version=version)
        current = self._skills.get(skill_id)
        if expected_parent_version is not None:
            actual = current.version if current is not None else None
            if actual != expected_parent_version:
                raise ValueError(
                    f"skill parent changed: expected {expected_parent_version}, got {actual}"
                )
        if (
            candidate.parent_version is not None
            and current is not None
            and candidate.parent_version != current.version
        ):
            raise ValueError("candidate is not based on the current promoted skill")
        active = replace(candidate, lifecycle=SkillLifecycle.ACTIVE)
        self._versions[skill_id][version] = active
        self._skills[skill_id] = active
        return active

    def retire(self, skill_id: str) -> SkillDefinition:
        current = self.get(skill_id)
        retired = replace(current, lifecycle=SkillLifecycle.RETIRED)
        self._versions[skill_id][current.version] = retired
        self._skills.pop(skill_id, None)
        return retired

    def get(self, skill_id: str, *, version: str | None = None) -> SkillDefinition:
        try:
            if version is None:
                return self._skills[skill_id]
            return self._versions[skill_id][version]
        except KeyError as exc:
            suffix = f"@{version}" if version else ""
            raise KeyError(f"unknown skill: {skill_id}{suffix}") from exc

    def current_version(self, skill_id: str) -> str | None:
        skill = self._skills.get(skill_id)
        return skill.version if skill is not None else None

    def versions(self, skill_id: str) -> list[SkillDefinition]:
        return sorted(
            self._versions.get(skill_id, {}).values(),
            key=lambda item: item.version,
        )

    def register_collection(self, collection: SkillCollection) -> None:
        unknown = [skill_id for skill_id in collection.skill_ids if skill_id not in self._skills]
        if unknown:
            raise ValueError(f"collection references unknown skills: {unknown}")
        self._collections[collection.collection_id] = collection

    def collection(self, collection_id: str) -> list[SkillDefinition]:
        try:
            definition = self._collections[collection_id]
        except KeyError as exc:
            raise KeyError(f"unknown skill collection: {collection_id}") from exc
        return [self.get(skill_id) for skill_id in definition.skill_ids]

    def collections(self) -> list[SkillCollection]:
        return sorted(self._collections.values(), key=lambda item: item.collection_id)

    def search(self, tags: Iterable[str]) -> list[SkillDefinition]:
        wanted = {tag.lower() for tag in tags}
        if not wanted:
            return self.list()
        return [
            skill
            for skill in self.list()
            if wanted.intersection(tag.lower() for tag in skill.tags)
        ]

    def for_workstream(self, workstream: str) -> list[SkillDefinition]:
        return [
            skill
            for skill in self.list()
            if not skill.workstreams or workstream in skill.workstreams
        ]

    def list(self) -> list[SkillDefinition]:
        return sorted(self._skills.values(), key=lambda skill: skill.skill_id)

    def list_all_versions(self) -> list[SkillDefinition]:
        return sorted(
            (skill for versions in self._versions.values() for skill in versions.values()),
            key=lambda skill: (skill.skill_id, skill.version),
        )

    def resolve_dependencies(self, skill_ids: Iterable[str]) -> list[SkillDefinition]:
        ordered: list[SkillDefinition] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(skill_id: str) -> None:
            if skill_id in visited:
                return
            if skill_id in visiting:
                raise ValueError(f"cyclic skill dependency detected at {skill_id}")
            visiting.add(skill_id)
            skill = self.get(skill_id)
            for dependency in skill.depends_on:
                visit(dependency)
            visiting.remove(skill_id)
            visited.add(skill_id)
            ordered.append(skill)

        for skill_id in skill_ids:
            visit(skill_id)
        return ordered


class SkillScheduler:
    """Rank promoted Skills under workstream, permission, latency and cost constraints."""

    _TOKEN = re.compile(r"[a-z0-9_]+")

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def schedule(self, request: SkillScheduleRequest) -> SkillSchedule:
        requested_tags = {item.lower() for item in request.tags}
        requested_intents = {item.lower() for item in request.intents}
        question_tokens = set(self._TOKEN.findall(request.question.lower()))
        permission_set = set(request.permissions) if request.permissions is not None else None

        ranked: list[tuple[float, SkillDefinition, str]] = []
        for skill in self.registry.list():
            if request.workstream and skill.workstreams and request.workstream not in skill.workstreams:
                continue
            if permission_set is not None and not set(skill.permissions).issubset(permission_set):
                continue
            if not request.allow_code_execution and skill.risk == SkillRisk.CODE_EXECUTION:
                continue

            tags = {item.lower() for item in skill.tags}
            intents = {item.lower() for item in skill.intents}
            description_tokens = set(self._TOKEN.findall(skill.description.lower()))
            skill_tokens = set(self._TOKEN.findall(skill.skill_id.lower()))
            score = 0.0
            reasons: list[str] = []

            if request.workstream and request.workstream in skill.workstreams:
                score += 4.0
                reasons.append("workstream")
            tag_overlap = len(requested_tags & tags)
            if tag_overlap:
                score += 2.0 * tag_overlap
                reasons.append("tag")
            intent_overlap = len(requested_intents & intents)
            if intent_overlap:
                score += 3.0 * intent_overlap
                reasons.append("intent")
            lexical_overlap = len(question_tokens & (tags | intents | description_tokens | skill_tokens))
            if lexical_overlap:
                score += min(3.0, 0.5 * lexical_overlap)
                reasons.append("question")
            if score <= 0 and request.workstream is None:
                continue
            ranked.append((score, skill, "+".join(reasons) or "eligible"))

        ranked.sort(
            key=lambda item: (
                -item[0],
                item[1].estimated_cost,
                item[1].estimated_latency_ms,
                item[1].skill_id,
            )
        )

        selected_ids: list[str] = []
        total_cost = 0.0
        total_latency = 0.0
        for _, skill, _ in ranked:
            if len(selected_ids) >= request.max_skills:
                break
            if skill.skill_id in selected_ids:
                continue
            next_cost = total_cost + skill.estimated_cost
            next_latency = total_latency + skill.estimated_latency_ms
            if request.max_estimated_cost is not None and next_cost > request.max_estimated_cost:
                continue
            if (
                request.max_estimated_latency_ms is not None
                and next_latency > request.max_estimated_latency_ms
            ):
                continue
            selected_ids.append(skill.skill_id)
            total_cost = next_cost
            total_latency = next_latency

        dependencies = self.registry.resolve_dependencies(selected_ids)
        if len(dependencies) > request.max_skills:
            dependencies = dependencies[: request.max_skills]

        rank_by_id = {skill.skill_id: (score, reason) for score, skill, reason in ranked}
        scheduled = tuple(
            ScheduledSkill(
                skill_id=skill.skill_id,
                version=skill.version,
                score=rank_by_id.get(skill.skill_id, (0.0, "dependency"))[0],
                reason=rank_by_id.get(skill.skill_id, (0.0, "dependency"))[1],
            )
            for skill in dependencies
        )
        return SkillSchedule(
            skills=scheduled,
            estimated_cost=sum(self.registry.get(item.skill_id).estimated_cost for item in scheduled),
            estimated_latency_ms=sum(
                self.registry.get(item.skill_id).estimated_latency_ms for item in scheduled
            ),
        )


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
            workstreams=("analytics",),
            intents=("metric", "compare", "trend"),
            implementation_ref="runtime.metric_analysis",
        ),
        SkillDefinition(
            skill_id="business.attribution",
            description="Drill down across dimensions and rank observed contributors.",
            input_schema={"metric": "str", "dimensions": "list[str]"},
            output_schema={"contributors": "list", "limitations": "list"},
            tool_dependencies=("contribution_analysis", "python_sandbox", "verification"),
            permissions=("analytics:read",),
            tags=("analytics", "attribution", "root-cause"),
            workstreams=("analytics",),
            intents=("attribution", "driver", "drilldown"),
            implementation_ref="runtime.attribution",
        ),
        SkillDefinition(
            skill_id="business.marketing_budget",
            description="Create a constrained marketing-budget allocation proposal.",
            input_schema={"budget": "number", "segments": "list"},
            output_schema={"allocation": "list", "expected_metrics": "dict"},
            tool_dependencies=("campaign_history", "optimizer", "campaign_api"),
            permissions=("marketing:read", "marketing:propose"),
            tags=("marketing", "budget", "operations"),
            workstreams=("marketing",),
            intents=("budget", "allocation"),
            implementation_ref="runtime.marketing_budget",
            risk=SkillRisk.REVERSIBLE_WRITE,
        ),
        SkillDefinition(
            skill_id="business.sales_expansion",
            description="Prioritize merchant or account opportunities for sales outreach.",
            input_schema={"market": "str", "capacity": "int"},
            output_schema={"leads": "list", "evidence": "list"},
            tool_dependencies=("merchant_profile", "opportunity_ranker", "crm"),
            permissions=("sales:read", "crm:propose"),
            tags=("sales", "merchant", "operations"),
            workstreams=("sales",),
            intents=("lead", "expansion", "outreach"),
            implementation_ref="runtime.sales_expansion",
            risk=SkillRisk.REVERSIBLE_WRITE,
        ),
        SkillDefinition(
            skill_id="business.monetization",
            description="Identify monetization opportunities and propose product matches.",
            input_schema={"merchant_scope": "list"},
            output_schema={"opportunities": "list", "revenue_estimate": "dict"},
            tool_dependencies=("merchant_profile", "product_catalog", "revenue_simulator"),
            permissions=("monetization:read", "monetization:propose"),
            tags=("monetization", "merchant", "operations"),
            workstreams=("monetization",),
            intents=("monetization", "opportunity"),
            implementation_ref="runtime.monetization",
        ),
        SkillDefinition(
            skill_id="runtime.verify_action",
            description="Verify evidence, permissions, budgets and approval before execution.",
            input_schema={"action": "object"},
            output_schema={"allowed": "bool", "reasons": "list"},
            tool_dependencies=("policy_engine", "audit_log"),
            permissions=("runtime:verify",),
            tags=("safety", "verification", "runtime"),
            intents=("verify", "guard"),
            implementation_ref="runtime.verify_action",
        ),
    ):
        registry.register(skill)
    return registry
