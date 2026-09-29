from __future__ import annotations

from eiw.retail.models import WorkstreamName
from eiw.retail.skill_system import retail_skill_registry
from eiw.runtime.skill_evolution import (
    PairedSkillEvolutionGate,
    SkillCandidateFactory,
    SkillEvolutionEngine,
    SkillEvolutionMetrics,
    SkillGapMiner,
    SkillTrajectoryFailure,
)
from eiw.runtime.skills import (
    SkillCollection,
    SkillDefinition,
    SkillLifecycle,
    SkillRegistry,
    SkillRisk,
    SkillScheduleRequest,
    SkillScheduler,
)


def _definition(
    skill_id: str,
    *,
    version: str = "1.0.0",
    parent_version: str | None = None,
    risk: SkillRisk = SkillRisk.READ_ONLY,
    permissions: tuple[str, ...] = ("analytics:read",),
) -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        version=version,
        parent_version=parent_version,
        description=f"{skill_id} store contribution analysis",
        input_schema={"question": "str"},
        output_schema={"rows": "list"},
        tool_dependencies=(f"tool.{skill_id}",),
        permissions=permissions,
        tags=("store", "contribution"),
        workstreams=("store",),
        intents=("driver", "attribution"),
        implementation_ref=f"test.{skill_id}",
        risk=risk,
    )


def _metrics(
    quality: float,
    *,
    safety: float = 1.0,
) -> SkillEvolutionMetrics:
    return SkillEvolutionMetrics(
        task_success=quality,
        quality_score=quality,
        tool_reliability=0.99,
        safety_compliance=safety,
        permission_compliance=1.0,
        average_cost=1.0,
        p95_latency_ms=100.0,
    )


def test_registry_versions_collections_and_promotion() -> None:
    registry = SkillRegistry()
    registry.register(_definition("store_contribution"))
    registry.register_collection(
        SkillCollection(
            collection_id="retail.store",
            description="Store specialist Skills",
            skill_ids=("store_contribution",),
        )
    )
    candidate = _definition(
        "store_contribution",
        version="1.1.0",
        parent_version="1.0.0",
    )
    registry.stage(candidate)

    assert registry.get("store_contribution").version == "1.0.0"
    assert registry.get("store_contribution", version="1.1.0").lifecycle == SkillLifecycle.CANDIDATE
    assert registry.collection("retail.store")[0].skill_id == "store_contribution"

    promoted = registry.promote(
        "store_contribution",
        "1.1.0",
        expected_parent_version="1.0.0",
    )
    assert promoted.lifecycle == SkillLifecycle.ACTIVE
    assert registry.get("store_contribution").version == "1.1.0"


def test_scheduler_respects_workstream_permissions_and_code_boundary() -> None:
    registry = SkillRegistry()
    registry.register(_definition("store_contribution"))
    registry.register(
        _definition(
            "store_code_probe",
            risk=SkillRisk.CODE_EXECUTION,
        )
    )
    registry.register(
        _definition(
            "store_sensitive",
            permissions=("analytics:read", "sensitive:read"),
        )
    )
    scheduler = SkillScheduler(registry)

    schedule = scheduler.schedule(
        SkillScheduleRequest(
            question="Which store contribution explains the decline?",
            workstream="store",
            permissions=("analytics:read",),
            max_skills=4,
            allow_code_execution=False,
        )
    )

    assert schedule.skill_ids == ("store_contribution",)


def test_retail_catalog_represents_and_organizes_twelve_promoted_skills() -> None:
    registry = retail_skill_registry()

    assert len(registry.list()) == 12
    assert len(registry.collections()) == len(WorkstreamName)
    assert {item.skill_id for item in registry.collection("retail.store")} == {
        "store_contribution",
        "store_anomaly",
        "store_commodity_scan",
    }

    schedule = SkillScheduler(registry).schedule(
        SkillScheduleRequest(
            question="Which stores explain the movement?",
            workstream="store",
            permissions=("analytics:read",),
            max_skills=3,
            allow_code_execution=False,
        )
    )
    assert set(schedule.skill_ids) == {
        "store_contribution",
        "store_anomaly",
        "store_commodity_scan",
    }


def test_failure_gap_can_revise_skill_and_promote_only_after_paired_gate() -> None:
    registry = SkillRegistry()
    registry.register(_definition("store_contribution"))
    gap = SkillGapMiner().mine(
        [
            SkillTrajectoryFailure(
                failure_id="f1",
                category="quality",
                summary="Store driver was missed.",
                workstream="store",
                required_capability="store attribution",
                attempted_skills=("store_contribution",),
                evidence_refs=("eval:case-1",),
                tool_refs=("tool.store_contribution",),
            ),
            SkillTrajectoryFailure(
                failure_id="f2",
                category="quality",
                summary="Store driver was missed.",
                workstream="store",
                required_capability="store attribution",
                attempted_skills=("store_contribution",),
                evidence_refs=("eval:case-2",),
                tool_refs=("tool.store_contribution",),
            ),
        ]
    )[0]
    assert gap.occurrences == 2

    candidate = SkillCandidateFactory().revise_skill_from_gap(
        registry.get("store_contribution"),
        gap,
        version="1.1.0",
        tags=("robust",),
    )
    engine = SkillEvolutionEngine(registry)
    engine.stage_candidate(candidate)

    def evaluator(skill: SkillDefinition | None) -> SkillEvolutionMetrics:
        return _metrics(0.90 if skill is not None and skill.version == "1.1.0" else 0.80)

    decision = engine.evaluate_candidate(
        "store_contribution",
        "1.1.0",
        evaluator=evaluator,
    )
    assert decision["comparison"]["passed"] is True
    assert decision["promoted"] is True
    assert registry.get("store_contribution").version == "1.1.0"


def test_skill_quality_gain_cannot_override_safety_regression() -> None:
    registry = SkillRegistry()
    registry.register(_definition("store_contribution"))
    gap = SkillGapMiner().mine(
        [
            SkillTrajectoryFailure(
                failure_id="f1",
                category="quality",
                summary="Store driver was missed.",
                workstream="store",
                required_capability="store attribution",
                attempted_skills=("store_contribution",),
                evidence_refs=("eval:case-1",),
            )
        ]
    )[0]
    candidate = SkillCandidateFactory().revise_skill_from_gap(
        registry.get("store_contribution"),
        gap,
        version="1.1.0-unsafe",
    )
    engine = SkillEvolutionEngine(
        registry,
        gate=PairedSkillEvolutionGate(max_latency_increase=None),
    )
    engine.stage_candidate(candidate)

    def evaluator(skill: SkillDefinition | None) -> SkillEvolutionMetrics:
        if skill is not None and skill.version == "1.1.0-unsafe":
            return _metrics(0.95, safety=0.95)
        return _metrics(0.80, safety=1.0)

    decision = engine.evaluate_candidate(
        "store_contribution",
        "1.1.0-unsafe",
        evaluator=evaluator,
    )
    assert decision["comparison"]["passed"] is False
    assert "safety_regression" in decision["comparison"]["reasons"]
    assert decision["promoted"] is False
    assert registry.get("store_contribution").version == "1.0.0"
