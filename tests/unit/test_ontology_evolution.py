from __future__ import annotations

from pathlib import Path

import eiw.ontology as ontology
from eiw.semantic.package import load_semantic_package


_REPO_ROOT = Path(__file__).resolve().parents[2]
_RETAIL_PACKAGE = (
    _REPO_ROOT
    / "semantic_packages"
    / "retail_complete_journey"
    / "semantic-package.yaml"
)


def _store() -> ontology.OntologyStore:
    package = load_semantic_package(_RETAIL_PACKAGE)
    state = ontology.SemanticPackageOntologyBuilder().build(
        package,
        ontology_id="retail",
        version="1.0.0",
    )
    store = ontology.OntologyStore()
    store.put(state, make_current=True)
    return store


def _metrics(*, quality: float, security: float = 1.0) -> ontology.EvolutionMetrics:
    return ontology.EvolutionMetrics(
        semantic_coverage=quality,
        driver_recall=quality,
        numeric_accuracy=1.0,
        security_resistance=security,
        permission_compliance=1.0,
        causal_discipline=1.0,
        average_cost=1.0,
        p95_latency_ms=100.0,
    )


def test_failure_is_attributed_and_grounded_candidate_is_promoted_only_after_gate() -> None:
    store = _store()
    signatures = ontology.FailureAttributor().attribute(
        [
            ontology.TrajectoryFailure(
                failure_id="f1",
                category="SEMANTIC",
                summary="Revenue requests repeatedly missed the governed sales concept.",
                semantic_refs=["metric:sales_value"],
            ),
            ontology.TrajectoryFailure(
                failure_id="f2",
                category="SEMANTIC",
                summary="Revenue requests repeatedly missed the governed sales concept.",
                semantic_refs=["metric:sales_value"],
            ),
        ]
    )
    assert len(signatures) == 1
    assert signatures[0].occurrences == 2
    assert signatures[0].level.value == "content"

    patch = ontology.GroundedPatchFactory().constraint_from_failure(
        signatures[0],
        parent_version="1.0.0",
        source_payload={"evaluation_case_ids": ["GC-101", "GC-102"]},
        description=(
            "Treat revenue-style requests as candidates for the governed "
            "sales_value concept before falling back to raw-schema exploration."
        ),
    )
    engine = ontology.SemanticEvolutionEngine(store)
    candidate = engine.stage_candidate(
        "retail",
        patch,
        candidate_version="1.1.0-candidate",
    )
    assert candidate.parent_version == "1.0.0"
    assert candidate.content_hash != store.current("retail").content_hash

    def evaluator(state):
        return _metrics(
            quality=0.92 if state.version == "1.0.0" else 0.94,
        )

    decision = engine.evaluate_candidate(
        "retail",
        "1.1.0-candidate",
        evaluator=evaluator,
    )
    assert decision["comparison"]["passed"] is True
    assert decision["promoted"] is True
    assert store.current("retail").version == "1.1.0-candidate"


def test_quality_gain_cannot_override_security_regression() -> None:
    store = _store()
    signature = ontology.FailureAttributor().attribute(
        [
            ontology.TrajectoryFailure(
                failure_id="f1",
                category="SEMANTIC",
                summary="A missing semantic constraint was observed.",
                semantic_refs=["metric:sales_value"],
            )
        ]
    )[0]
    patch = ontology.GroundedPatchFactory().constraint_from_failure(
        signature,
        parent_version="1.0.0",
        source_payload={"case_id": "GC-200"},
        description="Candidate learned semantic constraint.",
    )
    engine = ontology.SemanticEvolutionEngine(store)
    engine.stage_candidate(
        "retail",
        patch,
        candidate_version="1.1.0-unsafe",
    )

    def evaluator(state):
        if state.version == "1.0.0":
            return _metrics(quality=0.90, security=1.0)
        return _metrics(quality=0.98, security=0.95)

    decision = engine.evaluate_candidate(
        "retail",
        "1.1.0-unsafe",
        evaluator=evaluator,
    )
    assert decision["comparison"]["passed"] is False
    assert "security_regression" in decision["comparison"]["reasons"]
    assert decision["promoted"] is False
    assert store.current("retail").version == "1.0.0"
