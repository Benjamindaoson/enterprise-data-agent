"""Persistence tables for phase-zero durable contracts.

These tables implement the persistence mapping for domain objects.
The Domain layer owns the business logic; these tables only handle storage.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from eiw.domain.enums import (
    HypothesisState,
    TaskState,
)

# Standard SQLAlchemy metadata for all tables
metadata = MetaData()


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all tables."""

    metadata = metadata

    type_annotation_map = {
        dict[str, Any]: JSON,
        list[str]: ARRAY(String),
        Decimal: Numeric(20, 4),
    }


# =============================================================================
# Task and Runtime
# =============================================================================


class AnalysisTaskTable(Base):
    """Persistence record for AnalysisTask."""

    __tablename__ = "analysis_task"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    user_id: Mapped[str] = mapped_column(String(200))
    tenant_id: Mapped[str] = mapped_column(String(200))
    policy_version: Mapped[str] = mapped_column(String(100))
    domain_id: Mapped[str] = mapped_column(String(200))
    business_question: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(50), default=TaskState.CREATED.value)
    semantic_package_version: Mapped[str | None] = mapped_column(String(100))
    dataset_snapshot_identifier: Mapped[str | None] = mapped_column(String(200))
    dataset_snapshot_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)

    # JSON fields for complex data
    user_context_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    scope_hint_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    lineage_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    clarification_requests_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    clarification_responses_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    runtime_checkpoint_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_analysis_task_tenant_state", "tenant_id", "state"),
        Index("ix_analysis_task_created_at", "created_at"),
    )


# =============================================================================
# Context and Plan
# =============================================================================


class AnalysisContextTable(Base):
    """Persistence record for AnalysisContext."""

    __tablename__ = "analysis_context"

    context_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    context_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Resolved intent
    intent_objective: Mapped[str] = mapped_column(Text)
    intent_metrics_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    intent_filters_json: Mapped[dict[str, list[str]]] = mapped_column(JSON)
    intent_periods_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    intent_requires_clarification: Mapped[bool] = mapped_column(Boolean)

    # Data availability
    source_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    semantic_assets_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    allowed_data_objects: Mapped[list[str]] = mapped_column(ARRAY(String))
    quality_warnings: Mapped[list[str]] = mapped_column(ARRAY(String))

    __table_args__ = (
        Index("ix_analysis_context_task_id", "task_id"),
    )


class AnalysisPlanTable(Base):
    """Persistence record for AnalysisPlan."""

    __tablename__ = "analysis_plan"

    plan_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    context_version: Mapped[str] = mapped_column(String(100))
    business_objective: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    completion_criteria: Mapped[list[str]] = mapped_column(ARRAY(Text))
    stop_conditions: Mapped[list[str]] = mapped_column(ARRAY(Text))

    __table_args__ = (
        Index("ix_analysis_plan_task_id", "task_id"),
    )


class HypothesisTable(Base):
    """Persistence record for Hypothesis."""

    __tablename__ = "hypothesis"

    hypothesis_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    statement: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(50), default=HypothesisState.PROPOSED.value)
    priority: Mapped[int] = mapped_column(Integer)
    evidence_ids: Mapped[list[str]] = mapped_column(ARRAY(String))
    limitations: Mapped[list[str]] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_hypothesis_task_id", "task_id"),
        Index("ix_hypothesis_state", "state"),
    )


# =============================================================================
# Execution and Evidence
# =============================================================================


class ExecutionRecordTable(Base):
    """Persistence record for ExecutionRecord."""

    __tablename__ = "execution_record"

    execution_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    tool_name: Mapped[str] = mapped_column(String(100))
    tool_version: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    result_row_count: Mapped[int | None] = mapped_column(Integer)
    result_hash: Mapped[str | None] = mapped_column(String(64))
    error_category: Mapped[str | None] = mapped_column(String(50))
    error_summary: Mapped[str | None] = mapped_column(Text)

    input_parameters_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    policy_checks: Mapped[list[str]] = mapped_column(ARRAY(String))

    __table_args__ = (
        Index("ix_execution_record_task_id", "task_id"),
    )


class ObservationTable(Base):
    """Persistence record for Observation."""

    __tablename__ = "observation"

    observation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("execution_record.execution_id"))
    observation_type: Mapped[str] = mapped_column(String(100))
    statement: Mapped[str] = mapped_column(Text)
    result_snapshot_uri: Mapped[str] = mapped_column(String(500))
    result_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    numeric_values_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    dimensions_json: Mapped[dict[str, str]] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_observation_task_id", "task_id"),
    )


class ValidationResultTable(Base):
    """Persistence record for ValidationResult."""

    __tablename__ = "validation_result"

    validation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    rule_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    subject_type: Mapped[str] = mapped_column(String(100))
    subject_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[str] = mapped_column(Text)
    expected: Mapped[str | None] = mapped_column(Text)
    actual: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_validation_result_task_id", "task_id"),
    )


class ClaimTable(Base):
    """Persistence record for Claim."""

    __tablename__ = "claim"

    claim_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    claim_type: Mapped[str] = mapped_column(String(50))
    statement: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    limitations: Mapped[list[str]] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_claim_task_id", "task_id"),
    )


class EvidenceTable(Base):
    """Persistence record for Evidence."""

    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    observation_id: Mapped[str] = mapped_column(String(36), ForeignKey("observation.observation_id"))
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("execution_record.execution_id"))
    tool_name: Mapped[str] = mapped_column(String(100))
    tool_version: Mapped[str] = mapped_column(String(100))
    computation_identifier: Mapped[str] = mapped_column(String(200))
    result_snapshot_uri: Mapped[str] = mapped_column(String(500))
    result_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    dataset_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    validation_ids: Mapped[list[str]] = mapped_column(ARRAY(String))

    __table_args__ = (
        Index("ix_evidence_task_id", "task_id"),
    )


class ClaimEvidenceTable(Base):
    """Link table for Claim-Evidence relationships."""

    __tablename__ = "claim_evidence"

    claim_id: Mapped[str] = mapped_column(String(36), ForeignKey("claim.claim_id"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence.evidence_id"), primary_key=True)
    relation: Mapped[str] = mapped_column(String(50))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ArtifactTable(Base):
    """Persistence record for Artifact."""

    __tablename__ = "artifact"

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    artifact_type: Mapped[str] = mapped_column(String(50))
    uri: Mapped[str] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64))
    classification: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    claim_ids: Mapped[list[str]] = mapped_column(ARRAY(String))
    evidence_ids: Mapped[list[str]] = mapped_column(ARRAY(String))

    __table_args__ = (
        Index("ix_artifact_task_id", "task_id"),
    )


# =============================================================================
# Events and Evaluation
# =============================================================================


class DomainEventTable(Base):
    """Persistence record for DomainEvent."""

    __tablename__ = "domain_event"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    event_type: Mapped[str] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    trace_ref_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_domain_event_task_id", "task_id"),
        Index("ix_domain_event_occurred_at", "occurred_at"),
    )


class AuditEventTable(Base):
    """Persistence record for AuditEvent."""

    __tablename__ = "audit_event"

    audit_event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("analysis_task.task_id"))
    actor_id: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(200))
    policy_version: Mapped[str] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_audit_event_actor_id", "actor_id"),
        Index("ix_audit_event_occurred_at", "occurred_at"),
    )


class EvaluationCaseTable(Base):
    """Persistence record for EvaluationCase."""

    __tablename__ = "evaluation_case"

    case_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    business_question: Mapped[str] = mapped_column(Text)
    suite_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user_context_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    expected_semantics_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    allowed_data_objects: Mapped[list[str]] = mapped_column(ARRAY(String))
    forbidden_data_objects: Mapped[list[str]] = mapped_column(ARRAY(String))
    expected_numeric_values_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    numeric_tolerance: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    required_hypothesis_topics: Mapped[list[str]] = mapped_column(ARRAY(String))
    required_claim_types: Mapped[list[str]] = mapped_column(ARRAY(String))
    acceptable_outcomes: Mapped[list[str]] = mapped_column(ARRAY(String))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String))


class EvaluationRunTable(Base):
    """Persistence record for EvaluationRun."""

    __tablename__ = "evaluation_run"

    evaluation_run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    suite_version: Mapped[str] = mapped_column(String(100))
    git_revision: Mapped[str | None] = mapped_column(String(40))
    model_provider_version: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvaluationResultTable(Base):
    """Persistence record for EvaluationResult."""

    __tablename__ = "evaluation_result"

    result_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_run.evaluation_run_id"))
    case_id: Mapped[str] = mapped_column(String(20), ForeignKey("evaluation_case.case_id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    failure_categories: Mapped[list[str]] = mapped_column(ARRAY(String))
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_evaluation_result_run_id", "evaluation_run_id"),
    )
