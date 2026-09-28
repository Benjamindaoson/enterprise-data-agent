"""Selective runtime access to promoted ontology versions."""

from __future__ import annotations

import re
from typing import Any

from eiw.ontology.models import BrowseHit, OntologyResolution
from eiw.ontology.store import OntologyStore

_TOKEN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(value) if token.strip()}


class OntologyRuntime:
    """Expose compact manifest + on-demand browse/resolve semantics."""

    def __init__(self, store: OntologyStore) -> None:
        self.store = store

    def manifest(self, ontology_id: str) -> dict[str, Any]:
        state = self.store.current(ontology_id)
        return {
            "ontology_id": ontology_id,
            "version": state.version,
            "content_hash": state.content_hash,
            "counts": {
                "terms": len(state.terms),
                "mappings": len(state.mappings),
                "constraints": len(state.constraints),
                "evidence": len(state.evidence),
                "relations": len(state.relations),
            },
            "tools": state.schema_state.tool_contracts,
            "source_kind": state.source_kind,
        }

    def manifests(self) -> dict[str, dict[str, Any]]:
        return {
            ontology_id: self.manifest(ontology_id)
            for ontology_id in self.store.ontology_ids()
            if self.store.has(ontology_id)
        }

    def browse(
        self,
        ontology_id: str,
        query: str,
        *,
        semantic_types: set[str] | None = None,
        limit: int = 8,
    ) -> list[BrowseHit]:
        state = self.store.current(ontology_id)
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        hits: list[BrowseHit] = []
        query_normalized = " ".join(query.lower().split())
        for term in state.terms.values():
            if semantic_types and term.semantic_type not in semantic_types:
                continue
            searchable_parts = [
                term.term_id,
                term.label,
                term.description,
                term.canonical_id or "",
                *term.aliases,
                *term.tags,
            ]
            searchable = " ".join(searchable_parts)
            candidate_tokens = _tokens(searchable)
            overlap = len(query_tokens & candidate_tokens)
            if overlap == 0 and query_normalized not in searchable.lower():
                continue
            token_score = overlap / max(1, len(query_tokens))
            phrase_bonus = (
                0.5
                if query_normalized
                and query_normalized in " ".join(searchable.lower().split())
                else 0.0
            )
            alias_bonus = 0.25 if any(
                alias.lower() in query_normalized
                for alias in term.aliases
                if alias.strip()
            ) else 0.0
            score = token_score + phrase_bonus + alias_bonus
            hits.append(
                BrowseHit(
                    term_id=term.term_id,
                    label=term.label,
                    semantic_type=term.semantic_type,
                    canonical_id=term.canonical_id,
                    score=round(score, 6),
                    summary=term.description,
                )
            )
        hits.sort(key=lambda item: (-item.score, item.term_id))
        return hits[: max(1, min(limit, 50))]

    def resolve(
        self,
        ontology_id: str,
        term_ids: list[str],
        *,
        include_evidence: bool = True,
    ) -> OntologyResolution:
        state = self.store.current(ontology_id)
        terms = []
        mapping_ids: set[str] = set()
        constraint_ids: set[str] = set()
        evidence_ids: set[str] = set()
        for term_id in term_ids:
            try:
                term = state.terms[term_id]
            except KeyError as exc:
                raise KeyError(f"unknown ontology term: {term_id}") from exc
            terms.append(term)
            mapping_ids.update(term.mapping_ids)
            constraint_ids.update(term.constraint_ids)
            evidence_ids.update(term.evidence_ids)

        mappings = [state.mappings[item] for item in sorted(mapping_ids)]
        constraints = [state.constraints[item] for item in sorted(constraint_ids)]
        for mapping in mappings:
            evidence_ids.update(mapping.evidence_ids)
        for constraint in constraints:
            evidence_ids.update(constraint.evidence_ids)

        relations = [
            relation
            for relation in state.relations.values()
            if relation.source_term_id in term_ids or relation.target_term_id in term_ids
        ]
        for relation in relations:
            evidence_ids.update(relation.evidence_ids)

        evidence = (
            [state.evidence[item] for item in sorted(evidence_ids)]
            if include_evidence
            else []
        )
        return OntologyResolution(
            ontology_id=ontology_id,
            version=state.version,
            content_hash=state.content_hash,
            terms=terms,
            mappings=mappings,
            constraints=constraints,
            evidence=evidence,
            relations=relations,
        )
