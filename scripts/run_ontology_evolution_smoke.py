#!/usr/bin/env python3
"""Deterministic contract smoke for the offline ontology promotion gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.ontology.builder import SemanticPackageOntologyBuilder
from eiw.ontology.evolution import (
    EvolutionMetrics,
    FailureAttributor,
    GroundedPatchFactory,
    SemanticEvolutionEngine,
    TrajectoryFailure,
)
from eiw.ontology.store import OntologyStore
from eiw.semantic.package import load_semantic_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assert-gate", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    package = load_semantic_package(
        root
        / "semantic_packages"
        / "retail_complete_journey"
        / "semantic-package.yaml"
    )
    initial = SemanticPackageOntologyBuilder().build(
        package,
        ontology_id="retail",
        version="smoke-v1",
    )
    store = OntologyStore()
    store.put(initial, make_current=True)

    signature = FailureAttributor().attribute(
        [
            TrajectoryFailure(
                failure_id="smoke-failure",
                category="SEMANTIC",
                summary="Revenue wording missed the governed sales metric.",
                semantic_refs=["metric:sales_value"],
            )
        ]
    )[0]
    patch = GroundedPatchFactory().constraint_from_failure(
        signature,
        parent_version="smoke-v1",
        source_payload={"fixture": "semantic-evolution-smoke"},
        description=(
            "Map revenue-style language to the governed sales concept before "
            "raw-schema exploration."
        ),
    )
    engine = SemanticEvolutionEngine(store)
    engine.stage_candidate(
        "retail",
        patch,
        candidate_version="smoke-v2-candidate",
    )

    def evaluator(state):
        improved = state.version == "smoke-v2-candidate"
        return EvolutionMetrics(
            semantic_coverage=0.96 if improved else 0.94,
            driver_recall=0.92 if improved else 0.90,
            numeric_accuracy=1.0,
            security_resistance=1.0,
            permission_compliance=1.0,
            causal_discipline=1.0,
            average_cost=1.0,
            p95_latency_ms=100.0,
        )

    result = engine.evaluate_candidate(
        "retail",
        "smoke-v2-candidate",
        evaluator=evaluator,
    )
    rendered = json.dumps(result, indent=2, default=str)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    if args.assert_gate:
        if not bool(result["comparison"]["passed"]):
            return 2
        if not bool(result["promoted"]):
            return 3
        if store.current("retail").version != "smoke-v2-candidate":
            return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
