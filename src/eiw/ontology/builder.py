"""Evidence-grounded builders for semantic packages and PostgreSQL catalogs."""

from __future__ import annotations

import re
from typing import Any

from eiw.connectors.postgres import EnterprisePostgresConnector
from eiw.ontology.models import (
    OntologyConstraint,
    OntologyEvidence,
    OntologyMapping,
    OntologyRelation,
    OntologyState,
    OntologyTerm,
    evidence_hash,
)
from eiw.semantic.package import SemanticPackage

_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    normalized = _SLUG.sub("_", value.lower()).strip("_")
    return normalized or "item"


def _label(value: str) -> str:
    return value.replace("__", " ").replace("_", " ").strip().title()


def _evidence(
    evidence_id: str,
    *,
    evidence_type: str,
    source_ref: str,
    payload: dict[str, Any],
) -> OntologyEvidence:
    return OntologyEvidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_ref=source_ref,
        payload=payload,
        sha256=evidence_hash(payload),
    )


class SemanticPackageOntologyBuilder:
    """Upgrade the existing static package into a queryable ontology state."""

    def build(
        self,
        package: SemanticPackage,
        *,
        ontology_id: str,
        version: str | None = None,
    ) -> OntologyState:
        version = version or package.package.version
        source_evidence = _evidence(
            "evidence:semantic-package",
            evidence_type="semantic_package",
            source_ref=f"semantic-package://{package.package.id}@{package.package.version}",
            payload={
                "package_id": package.package.id,
                "package_version": package.package.version,
                "content_hash": package.content_hash,
            },
        )
        evidence = {source_evidence.evidence_id: source_evidence}
        terms: dict[str, OntologyTerm] = {}
        mappings: dict[str, OntologyMapping] = {}
        constraints: dict[str, OntologyConstraint] = {}

        for metric in package.metrics:
            term_id = f"metric:{metric.id}"
            mapping_id = f"mapping:metric:{metric.id}"
            mappings[mapping_id] = OntologyMapping(
                mapping_id=mapping_id,
                term_id=term_id,
                source_type="semantic_package",
                source_ref=(
                    f"semantic-package://{package.package.id}/metric/{metric.id}"
                ),
                expression=metric.expression,
                evidence_ids=[source_evidence.evidence_id],
            )
            aliases = [metric.id, metric.label]
            if metric.description:
                aliases.append(metric.description)
            terms[term_id] = OntologyTerm(
                term_id=term_id,
                label=metric.label,
                description=metric.description or "",
                aliases=aliases,
                semantic_type="metric",
                canonical_id=metric.id,
                mapping_ids=[mapping_id],
                evidence_ids=[source_evidence.evidence_id],
                tags=["metric", metric.unit],
            )

        for dimension in package.dimensions:
            term_id = f"dimension:{dimension.id}"
            mapping_id = f"mapping:dimension:{dimension.id}"
            mappings[mapping_id] = OntologyMapping(
                mapping_id=mapping_id,
                term_id=term_id,
                source_type="semantic_package",
                source_ref=dimension.source,
                expression=dimension.source,
                evidence_ids=[source_evidence.evidence_id],
            )
            terms[term_id] = OntologyTerm(
                term_id=term_id,
                label=dimension.label,
                aliases=[dimension.id, dimension.label, *dimension.attributes],
                semantic_type="dimension",
                canonical_id=dimension.id,
                mapping_ids=[mapping_id],
                evidence_ids=[source_evidence.evidence_id],
                tags=["dimension", dimension.grain or ""],
            )

        for index, rule in enumerate(package.business_rules, start=1):
            rule_id = str(rule.get("id") or f"business_rule_{index}")
            constraint_id = f"constraint:{rule_id}"
            constraints[constraint_id] = OntologyConstraint(
                constraint_id=constraint_id,
                constraint_type="business_rule",
                description=str(rule.get("description") or ""),
                severity="hard",
                source_ref=(
                    f"semantic-package://{package.package.id}/business-rule/{rule_id}"
                ),
                evidence_ids=[source_evidence.evidence_id],
            )

        for index, rule in enumerate(package.quality_rules, start=1):
            rule_id = str(rule.get("id") or f"quality_rule_{index}")
            constraint_id = f"constraint:{rule_id}"
            constraints[constraint_id] = OntologyConstraint(
                constraint_id=constraint_id,
                constraint_type="quality_rule",
                description=str(rule.get("description") or ""),
                severity="warning",
                source_ref=(
                    f"semantic-package://{package.package.id}/quality-rule/{rule_id}"
                ),
                evidence_ids=[source_evidence.evidence_id],
            )

        return OntologyState(
            ontology_id=ontology_id,
            version=version,
            source_kind="semantic_package",
            terms=terms,
            mappings=mappings,
            constraints=constraints,
            evidence=evidence,
            metadata={
                "source_package_id": package.package.id,
                "source_package_hash": package.content_hash,
            },
        )


class PostgresOntologyBuilder:
    """Construct a grounded initial ontology from a governed PostgreSQL source."""

    def __init__(self, connector: EnterprisePostgresConnector) -> None:
        self.connector = connector

    def build(
        self,
        *,
        ontology_id: str,
        version: str = "1.0.0",
        workload: list[str] | None = None,
    ) -> OntologyState:
        catalog = self.connector.introspect()
        package = self.connector.infer_semantic_package(
            package_id=f"{ontology_id}_inferred",
            version=version,
        )
        workload_tokens = {
            token
            for item in workload or []
            for token in _slug(item).split("_")
            if token
        }

        terms: dict[str, OntologyTerm] = {}
        mappings: dict[str, OntologyMapping] = {}
        constraints: dict[str, OntologyConstraint] = {}
        evidence: dict[str, OntologyEvidence] = {}
        relations: dict[str, OntologyRelation] = {}

        foreign_keys: dict[str, list[dict[str, Any]]] = {}
        for schema in catalog.get("schemas", []):
            for table in schema.get("tables", []):
                table_name = str(table["name"])
                foreign_keys[table_name] = list(table.get("foreign_keys", []))
                entity_id = f"entity:{table_name}"
                terms[entity_id] = OntologyTerm(
                    term_id=entity_id,
                    label=_label(table_name),
                    description=f"Governed PostgreSQL table {table_name}.",
                    aliases=[table_name],
                    semantic_type="entity",
                    canonical_id=table_name,
                    tags=["postgresql", "table"],
                )

        probe_cache: dict[tuple[str, str], OntologyEvidence] = {}

        def probe(table: str, column: str) -> OntologyEvidence:
            key = (table, column)
            cached = probe_cache.get(key)
            if cached is not None:
                return cached
            result = self.connector.probe_column(
                package.schema_name,
                table,
                column,
            )
            evidence_id = f"evidence:probe:{table}:{column}"
            item = _evidence(
                evidence_id,
                evidence_type="postgres_column_probe",
                source_ref=f"postgresql://{package.schema_name}.{table}.{column}",
                payload=result,
            )
            probe_cache[key] = item
            evidence[evidence_id] = item
            return item

        def workload_score(*values: str) -> float:
            tokens = {token for value in values for token in _slug(value).split("_") if token}
            if not workload_tokens:
                return 0.0
            return len(tokens & workload_tokens) / max(1, len(tokens))

        for metric_id, metric in package.metrics.items():
            item_evidence = probe(metric.table, metric.column)
            term_id = f"metric:{metric_id}"
            mapping_id = f"mapping:metric:{metric_id}"
            mappings[mapping_id] = OntologyMapping(
                mapping_id=mapping_id,
                term_id=term_id,
                source_type="postgresql",
                source_ref=(
                    f"postgresql://{package.schema_name}."
                    f"{metric.table}.{metric.column}"
                ),
                table=metric.table,
                column=metric.column,
                aggregation=metric.aggregation,
                evidence_ids=[item_evidence.evidence_id],
            )
            terms[term_id] = OntologyTerm(
                term_id=term_id,
                label=_label(metric.column),
                description=(
                    f"Inferred {metric.aggregation} metric over "
                    f"{metric.table}.{metric.column}; requires human semantic review "
                    "before business-critical use."
                ),
                aliases=[metric_id, metric.column, _label(metric.column)],
                semantic_type="metric",
                canonical_id=metric_id,
                mapping_ids=[mapping_id],
                evidence_ids=[item_evidence.evidence_id],
                tags=["inferred", "postgresql", "needs_semantic_review"],
                metadata={
                    "workload_relevance": workload_score(metric_id, metric.column),
                },
            )
            relation_id = f"relation:{term_id}:belongs_to:{metric.table}"
            relations[relation_id] = OntologyRelation(
                relation_id=relation_id,
                source_term_id=term_id,
                target_term_id=f"entity:{metric.table}",
                relation_type="belongs_to",
                evidence_ids=[item_evidence.evidence_id],
            )

        for dimension_id, dimension in package.dimensions.items():
            item_evidence = probe(dimension.table, dimension.column)
            term_id = f"dimension:{dimension_id}"
            mapping_id = f"mapping:dimension:{dimension_id}"
            mappings[mapping_id] = OntologyMapping(
                mapping_id=mapping_id,
                term_id=term_id,
                source_type="postgresql",
                source_ref=(
                    f"postgresql://{package.schema_name}."
                    f"{dimension.table}.{dimension.column}"
                ),
                table=dimension.table,
                column=dimension.column,
                evidence_ids=[item_evidence.evidence_id],
            )
            terms[term_id] = OntologyTerm(
                term_id=term_id,
                label=_label(dimension.column),
                description=(
                    f"Inferred dimension from {dimension.table}.{dimension.column}; "
                    "requires human semantic review before business-critical use."
                ),
                aliases=[dimension_id, dimension.column, _label(dimension.column)],
                semantic_type="dimension",
                canonical_id=dimension_id,
                mapping_ids=[mapping_id],
                evidence_ids=[item_evidence.evidence_id],
                tags=["inferred", "postgresql", "needs_semantic_review"],
                metadata={
                    "workload_relevance": workload_score(
                        dimension_id,
                        dimension.column,
                    ),
                },
            )
            relation_id = f"relation:{term_id}:belongs_to:{dimension.table}"
            relations[relation_id] = OntologyRelation(
                relation_id=relation_id,
                source_term_id=term_id,
                target_term_id=f"entity:{dimension.table}",
                relation_type="belongs_to",
                evidence_ids=[item_evidence.evidence_id],
            )

        for table_name, keys in foreign_keys.items():
            for index, key in enumerate(keys, start=1):
                target = str(key.get("referred_table") or "")
                if not target:
                    continue
                source_id = f"entity:{table_name}"
                target_id = f"entity:{target}"
                if source_id not in terms or target_id not in terms:
                    continue
                relation_id = f"relation:fk:{table_name}:{target}:{index}"
                relations[relation_id] = OntologyRelation(
                    relation_id=relation_id,
                    source_term_id=source_id,
                    target_term_id=target_id,
                    relation_type="references",
                )

        constraints["constraint:governed-read-only"] = OntologyConstraint(
            constraint_id="constraint:governed-read-only",
            constraint_type="execution_policy",
            description=(
                "Ontology-derived PostgreSQL analysis remains read-only and subject "
                "to connector schema/table/column allowlists."
            ),
            severity="hard",
            source_ref="runtime://postgres-permission-policy",
        )

        return OntologyState(
            ontology_id=ontology_id,
            version=version,
            source_kind="postgresql_builder",
            terms=terms,
            mappings=mappings,
            constraints=constraints,
            evidence=evidence,
            relations=relations,
            metadata={
                "schema_name": package.schema_name,
                "workload_size": len(workload or []),
                "builder": "PostgresOntologyBuilder-v1",
                "human_review_required": True,
                "raw_sample_values_stored": False,
            },
        )
