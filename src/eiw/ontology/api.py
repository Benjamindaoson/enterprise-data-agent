"""FastAPI surface for selective ontology access and staged onboarding."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from eiw.connectors.postgres import EnterprisePostgresConnector
from eiw.ontology.builder import PostgresOntologyBuilder
from eiw.ontology.runtime import OntologyRuntime


class OntologyBrowseRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    semantic_types: set[str] = Field(default_factory=set)
    limit: int = Field(default=8, ge=1, le=50)


class OntologyResolveRequest(BaseModel):
    term_ids: list[str] = Field(min_length=1, max_length=50)
    include_evidence: bool = True


class OntologyPostgresBuildRequest(BaseModel):
    ontology_id: str = Field(min_length=1, max_length=128)
    version: str = Field(default="1.0.0", min_length=1, max_length=64)
    workload: list[str] = Field(default_factory=list, max_length=200)
    promote: bool = False


def create_ontology_router(
    runtime: OntologyRuntime,
    *,
    postgres_connector_factory: Callable[[], EnterprisePostgresConnector] | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/ontology", tags=["ontology"])

    @router.get("/status")
    def status() -> dict[str, object]:
        return {"ontologies": runtime.manifests()}

    @router.get("/{ontology_id}/manifest")
    def manifest(ontology_id: str) -> dict[str, object]:
        try:
            return runtime.manifest(ontology_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/{ontology_id}/browse")
    def browse(
        ontology_id: str,
        request: OntologyBrowseRequest,
    ) -> dict[str, object]:
        try:
            hits = runtime.browse(
                ontology_id,
                request.query,
                semantic_types=request.semantic_types or None,
                limit=request.limit,
            )
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"items": [item.model_dump(mode="json") for item in hits]}

    @router.post("/{ontology_id}/resolve")
    def resolve(
        ontology_id: str,
        request: OntologyResolveRequest,
    ) -> dict[str, object]:
        try:
            resolution = runtime.resolve(
                ontology_id,
                request.term_ids,
                include_evidence=request.include_evidence,
            )
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return resolution.model_dump(mode="json")

    @router.post("/build/postgres")
    def build_postgres(
        request: OntologyPostgresBuildRequest,
    ) -> dict[str, object]:
        if postgres_connector_factory is None:
            raise HTTPException(503, "PostgreSQL ontology builder is not configured")
        try:
            connector = postgres_connector_factory()
            state = PostgresOntologyBuilder(connector).build(
                ontology_id=request.ontology_id,
                version=request.version,
                workload=request.workload,
            )
            runtime.store.put(state)
            if request.promote:
                runtime.store.promote(request.ontology_id, request.version)
            return {
                "ontology_id": state.ontology_id,
                "version": state.version,
                "content_hash": state.content_hash,
                "promoted": request.promote,
                "human_review_required": True,
                "manifest": (
                    runtime.manifest(request.ontology_id)
                    if request.promote
                    else {
                        "terms": len(state.terms),
                        "mappings": len(state.mappings),
                        "constraints": len(state.constraints),
                        "evidence": len(state.evidence),
                    }
                ),
            }
        except HTTPException:
            raise
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except (KeyError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502, f"Ontology build failed: {exc}") from exc

    @router.post("/{ontology_id}/versions/{version}/promote")
    def promote(ontology_id: str, version: str) -> dict[str, object]:
        try:
            state = runtime.store.promote(ontology_id, version)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {
            "ontology_id": ontology_id,
            "version": version,
            "content_hash": state.content_hash,
            "promoted": True,
        }

    return router
