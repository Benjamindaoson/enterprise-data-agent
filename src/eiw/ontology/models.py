"""Typed ontology contracts used by the semantic-evolution runtime."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class OntologyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OntologyLevel(StrEnum):
    CONTENT = "content"
    SCHEMA = "schema"
    TOOL = "tool"


class OntologyEvidence(OntologyModel):
    evidence_id: str
    evidence_type: str
    source_ref: str
    payload: dict[str, Any] = Field(default_factory=dict)
    sha256: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OntologyMapping(OntologyModel):
    mapping_id: str
    term_id: str
    source_type: Literal["postgresql", "semantic_package", "derived"]
    source_ref: str
    table: str | None = None
    column: str | None = None
    expression: str | None = None
    aggregation: str | None = None
    columns: list[str] = Field(default_factory=list)
    operator: Literal["column", "multiply", "add", "subtract", "divide"] | None = None
    join_path: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class OntologyConstraint(OntologyModel):
    constraint_id: str
    constraint_type: str
    description: str
    severity: Literal["info", "warning", "hard"] = "warning"
    term_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ref: str | None = None


class OntologyTerm(OntologyModel):
    term_id: str
    label: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    semantic_type: Literal["metric", "dimension", "entity", "concept"] = "concept"
    canonical_id: str | None = None
    mapping_ids: list[str] = Field(default_factory=list)
    constraint_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OntologyRelation(OntologyModel):
    relation_id: str
    source_term_id: str
    target_term_id: str
    relation_type: str
    evidence_ids: list[str] = Field(default_factory=list)


class OntologySchemaState(OntologyModel):
    version: str = "1.0.0"
    object_families: list[str] = Field(
        default_factory=lambda: ["term", "mapping", "constraint", "evidence"]
    )
    relation_types: list[str] = Field(
        default_factory=lambda: [
            "belongs_to",
            "equivalent_to",
            "derived_from",
            "associated_with",
        ]
    )
    tool_contracts: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "browse": {"inputs": ["query", "semantic_types", "limit"]},
            "resolve": {"inputs": ["term_ids", "include_evidence"]},
        }
    )


class OntologyState(OntologyModel):
    ontology_id: str
    version: str
    parent_version: str | None = None
    source_kind: str
    schema_state: OntologySchemaState = Field(
        default_factory=OntologySchemaState,
        validation_alias=AliasChoices("schema_state", "schema"),
    )
    terms: dict[str, OntologyTerm] = Field(default_factory=dict)
    mappings: dict[str, OntologyMapping] = Field(default_factory=dict)
    constraints: dict[str, OntologyConstraint] = Field(default_factory=dict)
    evidence: dict[str, OntologyEvidence] = Field(default_factory=dict)
    relations: dict[str, OntologyRelation] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def content_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"created_at"})
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @model_validator(mode="after")
    def references_are_valid(self) -> OntologyState:
        for mapping in self.mappings.values():
            if mapping.term_id not in self.terms:
                raise ValueError(f"mapping references unknown term: {mapping.term_id}")
            for evidence_id in mapping.evidence_ids:
                if evidence_id not in self.evidence:
                    raise ValueError(
                        f"mapping references unknown evidence: {evidence_id}"
                    )
        for constraint in self.constraints.values():
            for term_id in constraint.term_ids:
                if term_id not in self.terms:
                    raise ValueError(
                        f"constraint references unknown term: {term_id}"
                    )
            for evidence_id in constraint.evidence_ids:
                if evidence_id not in self.evidence:
                    raise ValueError(
                        f"constraint references unknown evidence: {evidence_id}"
                    )
        for term in self.terms.values():
            for mapping_id in term.mapping_ids:
                if mapping_id not in self.mappings:
                    raise ValueError(
                        f"term references unknown mapping: {mapping_id}"
                    )
            for constraint_id in term.constraint_ids:
                if constraint_id not in self.constraints:
                    raise ValueError(
                        f"term references unknown constraint: {constraint_id}"
                    )
            for evidence_id in term.evidence_ids:
                if evidence_id not in self.evidence:
                    raise ValueError(
                        f"term references unknown evidence: {evidence_id}"
                    )
        for relation in self.relations.values():
            if relation.source_term_id not in self.terms:
                raise ValueError(
                    f"relation references unknown source term: {relation.source_term_id}"
                )
            if relation.target_term_id not in self.terms:
                raise ValueError(
                    f"relation references unknown target term: {relation.target_term_id}"
                )
        return self


class BrowseHit(OntologyModel):
    term_id: str
    label: str
    semantic_type: str
    canonical_id: str | None = None
    score: float = Field(ge=0.0)
    summary: str = ""


class OntologyResolution(OntologyModel):
    ontology_id: str
    version: str
    content_hash: str
    terms: list[OntologyTerm]
    mappings: list[OntologyMapping]
    constraints: list[OntologyConstraint]
    evidence: list[OntologyEvidence]
    relations: list[OntologyRelation]


class FailureSignature(OntologyModel):
    signature_id: str
    level: OntologyLevel
    category: str
    summary: str
    semantic_refs: list[str] = Field(default_factory=list)
    tool_refs: list[str] = Field(default_factory=list)
    occurrences: int = Field(default=1, ge=1)
    expected_effect: str = ""


class OntologyPatch(OntologyModel):
    patch_id: str
    parent_version: str
    level: OntologyLevel
    hypothesis: str
    evidence: list[OntologyEvidence] = Field(default_factory=list)
    upsert_terms: list[OntologyTerm] = Field(default_factory=list)
    upsert_mappings: list[OntologyMapping] = Field(default_factory=list)
    upsert_constraints: list[OntologyConstraint] = Field(default_factory=list)
    upsert_relations: list[OntologyRelation] = Field(default_factory=list)
    remove_ids: list[str] = Field(default_factory=list)
    schema_update: dict[str, Any] = Field(default_factory=dict)
    tool_update: dict[str, Any] = Field(default_factory=dict)


def evidence_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
