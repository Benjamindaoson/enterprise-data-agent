"""FastAPI surface for the governed PostgreSQL enterprise connector."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from eiw.connectors.postgres import (
    ConnectorAnalysisRequest,
    EnterprisePostgresConnector,
    PostgresPermissionPolicy,
    PostgresSemanticPackage,
)


class PostgresAnalysisEnvelope(BaseModel):
    semantic_package: PostgresSemanticPackage
    request: ConnectorAnalysisRequest


def connector_from_env() -> EnterprisePostgresConnector:
    database_url = os.getenv("EIW_ENTERPRISE_POSTGRES_URL", "").strip()
    schemas = {
        item.strip()
        for item in os.getenv("EIW_ENTERPRISE_POSTGRES_SCHEMAS", "").split(",")
        if item.strip()
    }
    tables = {
        item.strip()
        for item in os.getenv("EIW_ENTERPRISE_POSTGRES_TABLES", "").split(",")
        if item.strip()
    }
    if not database_url:
        raise HTTPException(503, "EIW_ENTERPRISE_POSTGRES_URL is not configured")
    if not schemas:
        raise HTTPException(
            503,
            "EIW_ENTERPRISE_POSTGRES_SCHEMAS must explicitly allow at least one schema",
        )
    return EnterprisePostgresConnector(
        database_url,
        policy=PostgresPermissionPolicy(
            allowed_schemas=schemas,
            allowed_tables=tables,
            max_rows=int(os.getenv("EIW_ENTERPRISE_POSTGRES_MAX_ROWS", "200")),
            statement_timeout_ms=int(
                os.getenv("EIW_ENTERPRISE_POSTGRES_TIMEOUT_MS", "5000")
            ),
        ),
    )


def create_postgres_connector_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/connectors/postgres", tags=["postgres-connector"])

    @router.get("/status")
    def status() -> dict[str, object]:
        configured = bool(os.getenv("EIW_ENTERPRISE_POSTGRES_URL", "").strip())
        schemas = [
            item.strip()
            for item in os.getenv("EIW_ENTERPRISE_POSTGRES_SCHEMAS", "").split(",")
            if item.strip()
        ]
        return {
            "configured": configured,
            "allowed_schemas": schemas,
            "mode": "read-only",
        }

    @router.get("/catalog")
    def catalog() -> dict[str, object]:
        try:
            return connector_from_env().introspect()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(502, f"PostgreSQL introspection failed: {exc}") from exc

    @router.get("/semantic-template")
    def semantic_template() -> dict[str, object]:
        try:
            return connector_from_env().infer_semantic_package().model_dump(mode="json")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(502, f"Semantic inference failed: {exc}") from exc

    @router.post("/analyze")
    def analyze(envelope: PostgresAnalysisEnvelope) -> dict[str, object]:
        try:
            result = connector_from_env().analyze(
                envelope.semantic_package,
                envelope.request,
            )
            return result.model_dump(mode="json")
        except HTTPException:
            raise
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except (KeyError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502, f"PostgreSQL analysis failed: {exc}") from exc

    return router
