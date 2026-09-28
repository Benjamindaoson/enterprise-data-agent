from __future__ import annotations

from pathlib import Path

import pytest

from eiw.ontology.builder import SemanticPackageOntologyBuilder
from eiw.ontology.runtime import OntologyRuntime
from eiw.ontology.store import OntologyStore
from eiw.semantic.package import load_semantic_package


_REPO_ROOT = Path(__file__).resolve().parents[2]
_RETAIL_PACKAGE = (
    _REPO_ROOT
    / "semantic_packages"
    / "retail_complete_journey"
    / "semantic-package.yaml"
)


def _runtime() -> OntologyRuntime:
    package = load_semantic_package(_RETAIL_PACKAGE)
    state = SemanticPackageOntologyBuilder().build(
        package,
        ontology_id="retail",
    )
    store = OntologyStore()
    store.put(state, make_current=True)
    return OntologyRuntime(store)


def test_semantic_package_becomes_selectively_queryable_ontology() -> None:
    runtime = _runtime()

    hits = runtime.browse("retail", "sales revenue by store", limit=5)

    assert hits
    assert any(hit.canonical_id == "sales_value" for hit in hits)
    assert any(hit.canonical_id == "store" for hit in hits)

    selected = next(hit for hit in hits if hit.canonical_id == "sales_value")
    resolved = runtime.resolve("retail", [selected.term_id])

    assert resolved.version
    assert resolved.mappings
    assert resolved.evidence
    assert resolved.mappings[0].expression
    assert len(resolved.content_hash) == 64


def test_manifest_is_compact_and_store_versions_are_immutable(tmp_path: Path) -> None:
    package = load_semantic_package(_RETAIL_PACKAGE)
    state = SemanticPackageOntologyBuilder().build(
        package,
        ontology_id="retail",
    )
    path = tmp_path / "ontology-store.json"
    store = OntologyStore(path)
    store.put(state, make_current=True)

    manifest = OntologyRuntime(store).manifest("retail")
    assert manifest["counts"]["terms"] > 0
    assert "tools" in manifest
    assert path.exists()

    restored = OntologyStore(path)
    assert restored.current("retail").content_hash == state.content_hash

    changed = state.model_copy(
        update={"metadata": {**state.metadata, "changed": True}}
    )
    with pytest.raises(ValueError, match="immutable"):
        restored.put(changed)
