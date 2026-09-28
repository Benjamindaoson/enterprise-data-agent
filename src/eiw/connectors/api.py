"""FastAPI surface for the optional enterprise PostgreSQL connector."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from eiw.connectors.postgres import (
    PostgresAnalysisRequest,
    PostgresConnectorConfig,
    PostgresDomainRuntime,
    PostgresEnterpriseConnector,
    load_postgres_semantic_config,
)
from eiw.runtime.orchestrator import BusinessAgentRuntime


def create_postgres_connector_router(
    *,
    business_runtime: BusinessAgentRuntime,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/connectors/postgres", tags=["connector-postgres"])
    domain_runtime: PostgresDomainRuntime | None = None

    def configured() -> bool:
        return bool(
            os.getenv("EIW_ENTERPRISE_DATABASE_URL", "").strip()
            and os.getenv("EIW_ENTERPRISE_SEMANTIC_CONFIG", "").strip()
        )

    def get_runtime() -> PostgresDomainRuntime:
        nonlocal domain_runtime
        if domain_runtime is not None:
            return domain_runtime
        database_url = os.getenv("EIW_ENTERPRISE_DATABASE_URL", "").strip()
        semantic_path = os.getenv("EIW_ENTERPRISE_SEMANTIC_CONFIG", "").strip()
        if not database_url or not semantic_path:
            raise HTTPException(
                503,
                "Configure EIW_ENTERPRISE_DATABASE_URL and "
                "EIW_ENTERPRISE_SEMANTIC_CONFIG to enable PostgreSQL analysis.",
            )
        try:
            semantic = load_postgres_semantic_config(Path(semantic_path))
            denied = [
                value.strip()
                for value in os.getenv("EIW_ENTERPRISE_DENIED_COLUMNS", "").split(",")
                if value.strip()
            ]
            connector = PostgresEnterpriseConnector(
                database_url,
                config=PostgresConnectorConfig(
                    allowed_schemas=[semantic.schema_name],
                    allowed_tables=[semantic.fact_table],
                    denied_columns=denied,
                    max_rows=int(os.getenv("EIW_ENTERPRISE_MAX_ROWS", "200")),
                    statement_timeout_ms=int(
                        os.getenv("EIW_ENTERPRISE_STATEMENT_TIMEOUT_MS", "15000")
                    ),
                ),
            )
            candidate = PostgresDomainRuntime(connector, semantic)
        except Exception as exc:
            raise HTTPException(503, f"PostgreSQL connector initialization failed: {exc}") from exc

        try:
            registered = business_runtime.domain_runtime(candidate.domain_id)
        except KeyError:
            business_runtime.register_domain(candidate)
            domain_runtime = candidate
        else:
            if not isinstance(registered, PostgresDomainRuntime):
                raise HTTPException(500, "postgres-enterprise domain id is already occupied")
            domain_runtime = registered
        return domain_runtime

    @router.get("/status")
    def status() -> dict[str, object]:
        payload: dict[str, object] = {
            "connector": "postgresql",
            "configured": configured(),
            "domain_id": PostgresDomainRuntime.domain_id,
        }
        if domain_runtime is not None:
            payload["ready"] = domain_runtime.connector.ping()
            payload["capabilities"] = domain_runtime.capabilities()
        else:
            payload["ready"] = False
        return payload

    @router.get("/catalog")
    def catalog() -> dict[str, object]:
        runtime = get_runtime()
        return runtime.catalog.model_dump(mode="json")

    @router.get("/semantic-package")
    def semantic_package() -> dict[str, object]:
        runtime = get_runtime()
        return runtime.semantic_package.model_dump(mode="json")

    @router.post("/analyze")
    def analyze(request: PostgresAnalysisRequest) -> dict[str, object]:
        get_runtime()
        response = business_runtime.analyze_domain(
            PostgresDomainRuntime.domain_id,
            request,
        )
        return response.model_dump(mode="json")

    return router
