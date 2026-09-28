"""Offline, evidence-gated ontology evolution from Agent failures."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from statistics import fmean
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from eiw.ontology.models import (
    FailureSignature,
    OntologyConstraint,
    OntologyEvidence,
    OntologyLevel,
    OntologyMapping,
    OntologyPatch,
    OntologyRelation,
    OntologySchemaState,
    OntologyState,
    OntologyTerm,
    evidence_hash,
)
from eiw.ontology.store import OntologyStore


class TrajectoryFailure(BaseModel):
    failure_id: str
    category: str
    summary: str
    semantic_refs: list[str] = Field(default_factory=list)
    tool_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class FailureAttributor:
    """Attribute recurrent failure signatures to content, schema, or tool level."""

    _SCHEMA_TOKENS = ("schema", "join", "column", "type", "cardinality")
    _TOOL_TOKENS = ("tool", "timeout", "invalid action", "parser", "executor")

    def attribute(
        self,
        failures: list[TrajectoryFailure],
    ) -> list[FailureSignature]:
        grouped: dict[tuple[str, OntologyLevel, tuple[str, ...]], list[TrajectoryFailure]] = {}
        for failure in failures:
            text = f"{failure.category} {failure.summary}".lower()
            if any(token in text for token in self._SCHEMA_TOKENS):
                level = OntologyLevel.SCHEMA
            elif any(token in text for token in self._TOOL_TOKENS):
                level = OntologyLevel.TOOL
            else:
                level = OntologyLevel.CONTENT
            refs = tuple(sorted(set(failure.semantic_refs)))
            grouped.setdefault((failure.category, level, refs), []).append(failure)

        signatures: list[FailureSignature] = []
        for (category, level, refs), items in sorted(
            grouped.items(),
            key=lambda item: (-len(item[1]), item[0][0]),
        ):
            tools = Counter(tool for item in items for tool in item.tool_refs)
            signatures.append(
                FailureSignature(
                    signature_id=f"sig-{uuid4().hex[:12]}",
                    level=level,
                    category=category,
                    summary=items[0].summary,
                    semantic_refs=list(refs),
                    tool_refs=[name for name, _ in tools.most_common()],
                    occurrences=len(items),
                    expected_effect=(
                        f"Reduce recurrent {category} failures without regressing "
                        "business correctness, safety, permissions or causal discipline."
                    ),
                )
            )
        return signatures


class GroundedPatchFactory:
    """Create bounded candidates only when explicit evidence is supplied."""

    def from_failure(
        self,
        signature: FailureSignature,
        *,
        parent_version: str,
        evidence: list[OntologyEvidence],
        terms: list[OntologyTerm] | None = None,
        mappings: list[OntologyMapping] | None = None,
        constraints: list[OntologyConstraint] | None = None,
        relations: list[OntologyRelation] | None = None,
        schema_update: dict[str, Any] | None = None,
        tool_update: dict[str, Any] | None = None,
    ) -> OntologyPatch:
        if not evidence:
            raise ValueError("ontology evolution requires grounded evidence")
        return OntologyPatch(
            patch_id=f"patch-{uuid4().hex[:12]}",
            parent_version=parent_version,
            level=signature.level,
            hypothesis=signature.expected_effect or signature.summary,
            evidence=evidence,
            upsert_terms=list(terms or []),
            upsert_mappings=list(mappings or []),
            upsert_constraints=list(constraints or []),
            upsert_relations=list(relations or []),
            schema_update=dict(schema_update or {}),
            tool_update=dict(tool_update or {}),
        )

    def constraint_from_failure(
        self,
        signature: FailureSignature,
        *,
        parent_version: str,
        source_payload: dict[str, Any],
        description: str,
    ) -> OntologyPatch:
        evidence_id = f"evidence:failure:{_safe_id(signature.signature_id)}"
        payload = {
            "signature_id": signature.signature_id,
            "category": signature.category,
            "occurrences": signature.occurrences,
            "semantic_refs": signature.semantic_refs,
            "source": source_payload,
        }
        evidence = OntologyEvidence(
            evidence_id=evidence_id,
            evidence_type="trajectory_failure",
            source_ref=f"trajectory://{signature.signature_id}",
            payload=payload,
            sha256=evidence_hash(payload),
        )
        constraint = OntologyConstraint(
            constraint_id=f"constraint:failure:{_safe_id(signature.signature_id)}",
            constraint_type="trajectory_learned_guard",
            description=description,
            severity="warning",
            term_ids=[
                term_id for term_id in signature.semantic_refs if ":" in term_id
            ],
            evidence_ids=[evidence_id],
            source_ref=f"trajectory://{signature.signature_id}",
        )
        return self.from_failure(
            signature,
            parent_version=parent_version,
            evidence=[evidence],
            constraints=[constraint],
        )


def _safe_id(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value)


def apply_patch(
    parent: OntologyState,
    patch: OntologyPatch,
    *,
    candidate_version: str,
) -> OntologyState:
    if patch.parent_version != parent.version:
        raise ValueError(
            f"patch parent {patch.parent_version} != current parent {parent.version}"
        )
    terms = dict(parent.terms)
    mappings = dict(parent.mappings)
    constraints = dict(parent.constraints)
    evidence = dict(parent.evidence)
    relations = dict(parent.relations)

    for item_id in patch.remove_ids:
        terms.pop(item_id, None)
        mappings.pop(item_id, None)
        constraints.pop(item_id, None)
        evidence.pop(item_id, None)
        relations.pop(item_id, None)

    for item in patch.evidence:
        evidence[item.evidence_id] = item
    for item in patch.upsert_terms:
        terms[item.term_id] = item
    for item in patch.upsert_mappings:
        mappings[item.mapping_id] = item
    for item in patch.upsert_constraints:
        constraints[item.constraint_id] = item
    for item in patch.upsert_relations:
        relations[item.relation_id] = item

    schema_payload = parent.schema_state.model_dump(mode="json")
    if patch.schema_update:
        schema_payload.update(patch.schema_update)
    if patch.tool_update:
        tool_contracts = dict(schema_payload.get("tool_contracts", {}))
        tool_contracts.update(patch.tool_update)
        schema_payload["tool_contracts"] = tool_contracts

    # Ensure any new term references its newly-added objects if the caller omitted
    # the reverse links. This keeps the content graph internally navigable.
    by_term_mappings: dict[str, list[str]] = {}
    for mapping in mappings.values():
        by_term_mappings.setdefault(mapping.term_id, []).append(mapping.mapping_id)
    by_term_constraints: dict[str, list[str]] = {}
    for constraint in constraints.values():
        for term_id in constraint.term_ids:
            by_term_constraints.setdefault(term_id, []).append(constraint.constraint_id)

    normalized_terms: dict[str, OntologyTerm] = {}
    for term_id, term in terms.items():
        normalized_terms[term_id] = term.model_copy(
            update={
                "mapping_ids": sorted(
                    set(term.mapping_ids) | set(by_term_mappings.get(term_id, []))
                ),
                "constraint_ids": sorted(
                    set(term.constraint_ids)
                    | set(by_term_constraints.get(term_id, []))
                ),
            }
        )

    return OntologyState(
        ontology_id=parent.ontology_id,
        version=candidate_version,
        parent_version=parent.version,
        source_kind="trajectory_evolution",
        schema_state=OntologySchemaState.model_validate(schema_payload),
        terms=normalized_terms,
        mappings=mappings,
        constraints=constraints,
        evidence=evidence,
        relations=relations,
        metadata={
            **parent.metadata,
            "candidate_patch_id": patch.patch_id,
            "candidate_level": patch.level.value,
            "candidate_hypothesis": patch.hypothesis,
        },
    )


@dataclass(frozen=True, slots=True)
class EvolutionMetrics:
    semantic_coverage: float
    driver_recall: float
    numeric_accuracy: float
    security_resistance: float
    permission_compliance: float
    causal_discipline: float
    average_cost: float
    p95_latency_ms: float

    @property
    def quality_score(self) -> float:
        return fmean((self.semantic_coverage, self.driver_recall))


@dataclass(frozen=True, slots=True)
class PairedEvolutionGate:
    min_quality_gain: float = 0.005
    max_numeric_drop: float = 0.0
    max_security_drop: float = 0.0
    max_permission_drop: float = 0.0
    max_causal_drop: float = 0.0
    max_cost_increase: float = 0.20
    max_latency_increase: float = 0.25

    def compare(
        self,
        baseline: EvolutionMetrics,
        candidate: EvolutionMetrics,
    ) -> dict[str, Any]:
        reasons: list[str] = []
        quality_gain = candidate.quality_score - baseline.quality_score
        if quality_gain < self.min_quality_gain:
            reasons.append("insufficient_quality_gain")
        if candidate.numeric_accuracy < baseline.numeric_accuracy - self.max_numeric_drop:
            reasons.append("numeric_accuracy_regression")
        if (
            candidate.security_resistance
            < baseline.security_resistance - self.max_security_drop
        ):
            reasons.append("security_regression")
        if (
            candidate.permission_compliance
            < baseline.permission_compliance - self.max_permission_drop
        ):
            reasons.append("permission_regression")
        if (
            candidate.causal_discipline
            < baseline.causal_discipline - self.max_causal_drop
        ):
            reasons.append("causal_discipline_regression")
        if baseline.average_cost > 0 and candidate.average_cost > (
            baseline.average_cost * (1 + self.max_cost_increase)
        ):
            reasons.append("cost_regression")
        if baseline.p95_latency_ms > 0 and candidate.p95_latency_ms > (
            baseline.p95_latency_ms * (1 + self.max_latency_increase)
        ):
            reasons.append("latency_regression")
        return {
            "passed": not reasons,
            "reasons": reasons,
            "quality_gain": quality_gain,
            "baseline_quality": baseline.quality_score,
            "candidate_quality": candidate.quality_score,
        }


class SemanticEvolutionEngine:
    """Stage, evaluate and promote ontology candidates entirely offline."""

    def __init__(
        self,
        store: OntologyStore,
        *,
        gate: PairedEvolutionGate | None = None,
    ) -> None:
        self.store = store
        self.gate = gate or PairedEvolutionGate()

    def stage_candidate(
        self,
        ontology_id: str,
        patch: OntologyPatch,
        *,
        candidate_version: str,
    ) -> OntologyState:
        parent = self.store.current(ontology_id)
        candidate = apply_patch(
            parent,
            patch,
            candidate_version=candidate_version,
        )
        self.store.put(candidate)
        return candidate

    def evaluate_candidate(
        self,
        ontology_id: str,
        candidate_version: str,
        *,
        evaluator: Callable[[OntologyState], EvolutionMetrics],
        promote: bool = True,
    ) -> dict[str, Any]:
        baseline = self.store.current(ontology_id)
        candidate = self.store.get(ontology_id, candidate_version)
        if candidate.parent_version != baseline.version:
            raise ValueError("candidate is not based on the current promoted ontology")

        baseline_metrics = evaluator(baseline)
        candidate_metrics = evaluator(candidate)
        comparison = self.gate.compare(baseline_metrics, candidate_metrics)
        promoted = False
        if comparison["passed"] and promote:
            self.store.promote(
                ontology_id,
                candidate_version,
                expected_parent_version=baseline.version,
            )
            promoted = True
        return {
            "ontology_id": ontology_id,
            "baseline_version": baseline.version,
            "candidate_version": candidate.version,
            "baseline_hash": baseline.content_hash,
            "candidate_hash": candidate.content_hash,
            "baseline_metrics": baseline_metrics.__dict__,
            "candidate_metrics": candidate_metrics.__dict__,
            "comparison": comparison,
            "promoted": promoted,
        }
