"""Workload- and failure-driven bounded semantic evolution."""

from __future__ import annotations

import re
from typing import Any

from eiw.connectors.postgres import EnterprisePostgresConnector
from eiw.ontology.evolution import TrajectoryFailure
from eiw.ontology.models import (
    OntologyConstraint,
    OntologyEvidence,
    OntologyLevel,
    OntologyMapping,
    OntologyPatch,
    OntologyState,
    OntologyTerm,
    evidence_hash,
)

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN.findall(value.lower()))


def _safe(value: str) -> str:
    return "_".join(_TOKEN.findall(value.lower())) or "concept"


class WorkloadSemanticEvolver:
    """Infer a small set of bounded business semantics from failed workload traces.

    This is deliberately not a general natural-language reasoner. It provides a
    deterministic reference evolution path for reproducible evaluation. A
    ModelDrivenPostgresOntologyBuilder can replace the proposal step while the
    same evidence, patch, and promotion contracts remain unchanged.
    """

    def __init__(self, connector: EnterprisePostgresConnector) -> None:
        self.connector = connector

    def propose_patch(
        self,
        parent: OntologyState,
        failures: list[TrajectoryFailure],
    ) -> OntologyPatch:
        questions = [
            str(item.details.get("question") or item.summary)
            for item in failures
        ]
        workload_text = " ".join(questions).lower()
        catalog = self.connector.introspect()
        columns = self._columns(catalog)
        evidence: dict[str, OntologyEvidence] = {}
        terms: list[OntologyTerm] = []
        mappings: list[OntologyMapping] = []
        constraints: list[OntologyConstraint] = []

        def probe(table: str, column: str) -> str:
            evidence_id = f"evidence:evolution-probe:{_safe(table)}:{_safe(column)}"
            if evidence_id not in evidence:
                payload = self.connector.probe_column(
                    self._schema_name(catalog),
                    table,
                    column,
                )
                evidence[evidence_id] = OntologyEvidence(
                    evidence_id=evidence_id,
                    evidence_type="postgres_column_probe",
                    source_ref=f"postgresql://{table}.{column}",
                    payload=payload,
                    sha256=evidence_hash(payload),
                )
            return evidence_id

        def add_metric(
            concept_id: str,
            label: str,
            aliases: list[str],
            *,
            table: str,
            refs: list[str],
            aggregation: str,
            operator: str = "column",
            description: str,
        ) -> None:
            term_id = f"metric:{concept_id}"
            if term_id in parent.terms or any(item.term_id == term_id for item in terms):
                return
            evidence_ids = [probe(table, column) for column in refs]
            mapping_id = f"mapping:{term_id}"
            expression = (
                refs[0]
                if operator == "column"
                else f"{refs[0]} {self._operator_symbol(operator)} {refs[1]}"
            )
            mappings.append(
                OntologyMapping(
                    mapping_id=mapping_id,
                    term_id=term_id,
                    source_type="postgresql",
                    source_ref=f"postgresql://{table}/" + ",".join(refs),
                    table=table,
                    column=refs[0],
                    expression=expression,
                    aggregation=aggregation,
                    columns=refs,
                    operator=operator,
                    evidence_ids=evidence_ids,
                )
            )
            terms.append(
                OntologyTerm(
                    term_id=term_id,
                    label=label,
                    description=description,
                    aliases=sorted({concept_id, label, *aliases}),
                    semantic_type="metric",
                    canonical_id=concept_id,
                    mapping_ids=[mapping_id],
                    evidence_ids=evidence_ids,
                    tags=["trajectory_evolved", "workload_grounded"],
                )
            )

        def add_dimension(
            concept_id: str,
            label: str,
            aliases: list[str],
            *,
            table: str,
            column: str,
        ) -> None:
            term_id = f"dimension:{concept_id}"
            if term_id in parent.terms or any(item.term_id == term_id for item in terms):
                return
            evidence_id = probe(table, column)
            mapping_id = f"mapping:{term_id}"
            mappings.append(
                OntologyMapping(
                    mapping_id=mapping_id,
                    term_id=term_id,
                    source_type="postgresql",
                    source_ref=f"postgresql://{table}.{column}",
                    table=table,
                    column=column,
                    expression=column,
                    columns=[column],
                    operator="column",
                    evidence_ids=[evidence_id],
                )
            )
            terms.append(
                OntologyTerm(
                    term_id=term_id,
                    label=label,
                    aliases=sorted({concept_id, label, *aliases}),
                    semantic_type="dimension",
                    canonical_id=concept_id,
                    mapping_ids=[mapping_id],
                    evidence_ids=[evidence_id],
                    tags=["trajectory_evolved", "workload_grounded"],
                )
            )

        quantity = self._find_column(columns, {"quantity", "qty"})
        unit_price = self._find_column(
            columns,
            {"unitprice", "unit", "price"},
            exact_preference={"unitprice", "unit_price"},
        )
        customer = self._find_column(
            columns,
            {"customerid", "customer", "client", "buyer"},
            exact_preference={"customerid", "customer_id"},
        )
        country = self._find_column(columns, {"country", "region", "market"})
        product = self._find_column(
            columns,
            {"stockcode", "product", "sku", "item"},
            exact_preference={"stockcode", "product_id", "sku"},
        )

        if (
            any(token in workload_text for token in ("revenue", "sales", "turnover", "gmv"))
            and quantity
            and unit_price
            and quantity[0] == unit_price[0]
        ):
            add_metric(
                "revenue",
                "Revenue",
                ["sales", "turnover", "gmv", "sales value"],
                table=quantity[0],
                refs=[quantity[1], unit_price[1]],
                aggregation="sum",
                operator="multiply",
                description=(
                    "Observed transaction revenue computed as Quantity × UnitPrice "
                    "and aggregated across the requested slice."
                ),
            )

        if any(
            phrase in workload_text
            for phrase in ("units", "unit volume", "quantity sold", "sales volume")
        ) and quantity:
            add_metric(
                "units",
                "Units Sold",
                ["units", "quantity sold", "sales volume", "volume"],
                table=quantity[0],
                refs=[quantity[1]],
                aggregation="sum",
                description="Total observed item quantity.",
            )

        if any(
            phrase in workload_text
            for phrase in ("average price", "average selling price", "unit price")
        ) and unit_price:
            add_metric(
                "average_unit_price",
                "Average Unit Price",
                ["average price", "selling price", "unit price", "asp"],
                table=unit_price[0],
                refs=[unit_price[1]],
                aggregation="avg",
                description="Average observed unit price.",
            )

        if any(
            phrase in workload_text
            for phrase in (
                "active customer",
                "unique customer",
                "customer count",
                "unique buyer",
                "buyer count",
            )
        ) and customer:
            add_metric(
                "active_customers",
                "Active Customers",
                ["active customers", "unique customers", "unique buyers", "customer count"],
                table=customer[0],
                refs=[customer[1]],
                aggregation="count_distinct",
                description="Count of distinct customers observed in the requested slice.",
            )

        if country:
            add_dimension(
                "country",
                "Country",
                ["country", "market", "geography"],
                table=country[0],
                column=country[1],
            )
        if product:
            add_dimension(
                "product",
                "Product",
                ["product", "sku", "stock code", "item"],
                table=product[0],
                column=product[1],
            )
        if customer:
            add_dimension(
                "customer",
                "Customer",
                ["customer", "buyer", "client"],
                table=customer[0],
                column=customer[1],
            )

        if "gross margin" in workload_text or "margin" in workload_text:
            cost_like = self._find_column(
                columns,
                {"cost", "cogs", "margin", "profit"},
            )
            if cost_like is None:
                evidence_id = "evidence:unsupported:gross_margin"
                payload = {
                    "questions": questions,
                    "catalog_columns": sorted(
                        f"{table}.{column}"
                        for table, table_columns in columns.items()
                        for column in table_columns
                    ),
                }
                evidence[evidence_id] = OntologyEvidence(
                    evidence_id=evidence_id,
                    evidence_type="workload_gap",
                    source_ref="trajectory://gross-margin-gap",
                    payload=payload,
                    sha256=evidence_hash(payload),
                )
                constraints.append(
                    OntologyConstraint(
                        constraint_id="constraint:unsupported:gross_margin",
                        constraint_type="unsupported_business_concept",
                        description=(
                            "Gross margin cannot be computed because the governed "
                            "catalog exposes no cost/COGS/profit field."
                        ),
                        severity="hard",
                        evidence_ids=[evidence_id],
                        source_ref="trajectory://gross-margin-gap",
                    )
                )

        failure_payload = {
            "failure_ids": [item.failure_id for item in failures],
            "categories": [item.category for item in failures],
            "questions": questions,
        }
        failure_evidence = OntologyEvidence(
            evidence_id="evidence:trajectory-workload",
            evidence_type="trajectory_failure_set",
            source_ref="trajectory://semantic-adaptation",
            payload=failure_payload,
            sha256=evidence_hash(failure_payload),
        )
        evidence[failure_evidence.evidence_id] = failure_evidence

        return OntologyPatch(
            patch_id="patch:workload-semantic-evolution",
            parent_version=parent.version,
            level=OntologyLevel.CONTENT,
            hypothesis=(
                "Ground recurrent business vocabulary in typed physical mappings "
                "while explicitly abstaining on unsupported financial concepts."
            ),
            evidence=list(evidence.values()),
            upsert_terms=terms,
            upsert_mappings=mappings,
            upsert_constraints=constraints,
        )

    @staticmethod
    def _schema_name(catalog: dict[str, Any]) -> str:
        schemas = catalog.get("schemas", [])
        if not schemas:
            raise ValueError("catalog contains no allowed schema")
        return str(schemas[0]["name"])

    @staticmethod
    def _columns(catalog: dict[str, Any]) -> dict[str, list[str]]:
        output: dict[str, list[str]] = {}
        for schema in catalog.get("schemas", []):
            for table in schema.get("tables", []):
                output[str(table["name"])] = [
                    str(column["name"])
                    for column in table.get("columns", [])
                ]
        return output

    @staticmethod
    def _find_column(
        columns: dict[str, list[str]],
        tokens: set[str],
        *,
        exact_preference: set[str] | None = None,
    ) -> tuple[str, str] | None:
        exact_preference = exact_preference or set()
        exact: list[tuple[str, str]] = []
        fuzzy: list[tuple[str, str, int]] = []
        for table, values in columns.items():
            for column in values:
                normalized = _safe(column)
                collapsed = normalized.replace("_", "")
                if normalized in exact_preference or collapsed in exact_preference:
                    exact.append((table, column))
                    continue
                column_tokens = _tokens(column)
                score = len(column_tokens & tokens)
                if score == 0 and any(token in collapsed for token in tokens):
                    score = 1
                if score:
                    fuzzy.append((table, column, score))
        if exact:
            return sorted(exact)[0]
        if not fuzzy:
            return None
        fuzzy.sort(key=lambda item: (-item[2], item[0], item[1]))
        return fuzzy[0][0], fuzzy[0][1]

    @staticmethod
    def _operator_symbol(operator: str) -> str:
        return {
            "multiply": "*",
            "add": "+",
            "subtract": "-",
            "divide": "/",
        }[operator]
