"""Failure-driven, evaluation-gated Skill evolution for the Agent runtime."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from statistics import fmean
from typing import Any
from uuid import uuid4

from eiw.runtime.skills import (
    SkillDefinition,
    SkillLifecycle,
    SkillRegistry,
    SkillRisk,
)


@dataclass(frozen=True, slots=True)
class SkillTrajectoryFailure:
    failure_id: str
    category: str
    summary: str
    workstream: str
    required_capability: str
    attempted_skills: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    tool_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillGapSignature:
    signature_id: str
    category: str
    workstream: str
    required_capability: str
    summary: str
    occurrences: int
    attempted_skills: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    tool_refs: tuple[str, ...]


class SkillGapMiner:
    """Collapse recurrent trajectory failures into bounded capability gaps."""

    def mine(self, failures: list[SkillTrajectoryFailure]) -> list[SkillGapSignature]:
        grouped: dict[tuple[str, str, str], list[SkillTrajectoryFailure]] = {}
        for failure in failures:
            key = (
                failure.category.strip().lower(),
                failure.workstream.strip().lower(),
                failure.required_capability.strip().lower(),
            )
            grouped.setdefault(key, []).append(failure)

        signatures: list[SkillGapSignature] = []
        for (category, workstream, capability), items in sorted(
            grouped.items(),
            key=lambda item: (-len(item[1]), item[0]),
        ):
            attempted = Counter(skill for item in items for skill in item.attempted_skills)
            tools = Counter(tool for item in items for tool in item.tool_refs)
            evidence = tuple(
                sorted({ref for item in items for ref in item.evidence_refs})
            )
            signatures.append(
                SkillGapSignature(
                    signature_id=f"skill-gap-{uuid4().hex[:12]}",
                    category=category,
                    workstream=workstream,
                    required_capability=capability,
                    summary=items[0].summary,
                    occurrences=len(items),
                    attempted_skills=tuple(name for name, _ in attempted.most_common()),
                    evidence_refs=evidence,
                    tool_refs=tuple(name for name, _ in tools.most_common()),
                )
            )
        return signatures


class SkillCandidateFactory:
    """Create Skill candidates only from evidence-backed capability gaps."""

    def new_skill_from_gap(
        self,
        gap: SkillGapSignature,
        *,
        skill_id: str,
        version: str,
        description: str,
        input_schema: dict[str, str],
        output_schema: dict[str, str],
        tool_dependencies: tuple[str, ...],
        permissions: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        intents: tuple[str, ...] = (),
        implementation_ref: str,
        risk: SkillRisk = SkillRisk.READ_ONLY,
        estimated_cost: float = 0.0,
        estimated_latency_ms: float = 0.0,
    ) -> SkillDefinition:
        if not gap.evidence_refs:
            raise ValueError("Skill evolution requires evidence-backed trajectory failures")
        return SkillDefinition(
            skill_id=skill_id,
            version=version,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            tool_dependencies=tool_dependencies,
            permissions=permissions,
            tags=tuple(sorted(set(tags) | {"evolved"})),
            workstreams=(gap.workstream,),
            intents=intents or (gap.required_capability,),
            implementation_ref=implementation_ref,
            risk=risk,
            lifecycle=SkillLifecycle.CANDIDATE,
            estimated_cost=estimated_cost,
            estimated_latency_ms=estimated_latency_ms,
            evidence_refs=gap.evidence_refs,
        )

    def revise_skill_from_gap(
        self,
        parent: SkillDefinition,
        gap: SkillGapSignature,
        *,
        version: str,
        description: str | None = None,
        tags: tuple[str, ...] = (),
        intents: tuple[str, ...] = (),
        tool_dependencies: tuple[str, ...] | None = None,
        implementation_ref: str | None = None,
    ) -> SkillDefinition:
        if not gap.evidence_refs:
            raise ValueError("Skill evolution requires evidence-backed trajectory failures")
        return replace(
            parent,
            version=version,
            parent_version=parent.version,
            description=description or parent.description,
            tags=tuple(sorted(set(parent.tags) | set(tags) | {"evolved"})),
            intents=tuple(sorted(set(parent.intents) | set(intents))),
            tool_dependencies=tool_dependencies or parent.tool_dependencies,
            implementation_ref=implementation_ref or parent.implementation_ref,
            lifecycle=SkillLifecycle.CANDIDATE,
            evidence_refs=tuple(sorted(set(parent.evidence_refs) | set(gap.evidence_refs))),
        )


@dataclass(frozen=True, slots=True)
class SkillEvolutionMetrics:
    task_success: float
    quality_score: float
    tool_reliability: float
    safety_compliance: float
    permission_compliance: float
    average_cost: float
    p95_latency_ms: float

    @property
    def utility(self) -> float:
        return fmean((self.task_success, self.quality_score, self.tool_reliability))


@dataclass(frozen=True, slots=True)
class PairedSkillEvolutionGate:
    min_utility_gain: float = 0.005
    max_safety_drop: float = 0.0
    max_permission_drop: float = 0.0
    max_reliability_drop: float = 0.0
    max_cost_increase: float | None = 0.20
    max_latency_increase: float | None = 0.25
    max_average_cost: float | None = None
    max_p95_latency_ms: float | None = None

    def compare(
        self,
        baseline: SkillEvolutionMetrics,
        candidate: SkillEvolutionMetrics,
    ) -> dict[str, Any]:
        reasons: list[str] = []
        utility_gain = candidate.utility - baseline.utility
        if utility_gain < self.min_utility_gain:
            reasons.append("insufficient_utility_gain")
        if candidate.tool_reliability < baseline.tool_reliability - self.max_reliability_drop:
            reasons.append("tool_reliability_regression")
        if candidate.safety_compliance < baseline.safety_compliance - self.max_safety_drop:
            reasons.append("safety_regression")
        if (
            candidate.permission_compliance
            < baseline.permission_compliance - self.max_permission_drop
        ):
            reasons.append("permission_regression")
        if (
            self.max_cost_increase is not None
            and baseline.average_cost > 0
            and candidate.average_cost > baseline.average_cost * (1 + self.max_cost_increase)
        ):
            reasons.append("cost_regression")
        if (
            self.max_latency_increase is not None
            and baseline.p95_latency_ms > 0
            and candidate.p95_latency_ms
            > baseline.p95_latency_ms * (1 + self.max_latency_increase)
        ):
            reasons.append("latency_regression")
        if self.max_average_cost is not None and candidate.average_cost > self.max_average_cost:
            reasons.append("absolute_cost_budget_exceeded")
        if (
            self.max_p95_latency_ms is not None
            and candidate.p95_latency_ms > self.max_p95_latency_ms
        ):
            reasons.append("absolute_latency_budget_exceeded")
        return {
            "passed": not reasons,
            "reasons": reasons,
            "utility_gain": utility_gain,
            "baseline_utility": baseline.utility,
            "candidate_utility": candidate.utility,
        }


class SkillEvolutionEngine:
    """Stage, paired-evaluate and promote Skill candidates offline."""

    def __init__(
        self,
        registry: SkillRegistry,
        *,
        gate: PairedSkillEvolutionGate | None = None,
    ) -> None:
        self.registry = registry
        self.gate = gate or PairedSkillEvolutionGate()

    def stage_candidate(self, candidate: SkillDefinition) -> SkillDefinition:
        if candidate.lifecycle != SkillLifecycle.CANDIDATE:
            candidate = replace(candidate, lifecycle=SkillLifecycle.CANDIDATE)
        self.registry.stage(candidate)
        return candidate

    def evaluate_candidate(
        self,
        skill_id: str,
        candidate_version: str,
        *,
        evaluator: Callable[[SkillDefinition | None], SkillEvolutionMetrics],
        promote: bool = True,
    ) -> dict[str, Any]:
        baseline_version = self.registry.current_version(skill_id)
        baseline = self.registry.get(skill_id) if baseline_version is not None else None
        candidate = self.registry.get(skill_id, version=candidate_version)
        if candidate.parent_version is not None and baseline_version != candidate.parent_version:
            raise ValueError("candidate is not based on the current promoted Skill")

        baseline_metrics = evaluator(baseline)
        candidate_metrics = evaluator(candidate)
        comparison = self.gate.compare(baseline_metrics, candidate_metrics)
        promoted = False
        if comparison["passed"] and promote:
            self.registry.promote(
                skill_id,
                candidate_version,
                expected_parent_version=baseline_version,
            )
            promoted = True
        return {
            "skill_id": skill_id,
            "baseline_version": baseline_version,
            "candidate_version": candidate_version,
            "baseline_metrics": asdict(baseline_metrics),
            "candidate_metrics": asdict(candidate_metrics),
            "comparison": comparison,
            "promoted": promoted,
        }
