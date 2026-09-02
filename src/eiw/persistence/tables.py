"""Physical table boundaries for durable state, evidence, audit, and evaluation.

JSON payloads preserve contract evolution while query-critical IDs, states, versions,
and timestamps remain first-class columns. PostgreSQL is the authoritative runtime
state store; a queue or tracing vendor is never a second source of truth.
"""

from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, MetaData, String, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData(naming_convention={"ix": "ix_%(column_0_label)s", "pk": "pk_%(table_name)s"})


def id_column() -> object:
    return __import__("sqlalchemy").Column(
        "id", UUID(as_uuid=True), primary_key=True, default=uuid4
    )


def timestamps(table_name: str) -> list[object]:
    sqlalchemy = __import__("sqlalchemy")
    return [
        sqlalchemy.Column(
            "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
        sqlalchemy.Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    ]


analysis_task = Table(
    "analysis_task",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column("tenant_id", String(200), nullable=False, index=True),
    __import__("sqlalchemy").Column("user_id", String(200), nullable=False, index=True),
    __import__("sqlalchemy").Column("domain_id", String(200), nullable=False),
    __import__("sqlalchemy").Column("business_question", Text, nullable=False),
    __import__("sqlalchemy").Column("state", String(40), nullable=False, index=True),
    __import__("sqlalchemy").Column(
        "parent_task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id")
    ),
    __import__("sqlalchemy").Column("context_version", String(100)),
    __import__("sqlalchemy").Column("semantic_package_version", String(100)),
    __import__("sqlalchemy").Column("dataset_snapshot_id", String(200)),
    __import__("sqlalchemy").Column("idempotency_key", String(200)),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("analysis_task"),
)

task_state = Table(
    "task_state",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("from_state", String(40)),
    __import__("sqlalchemy").Column("to_state", String(40), nullable=False),
    __import__("sqlalchemy").Column("reason", Text),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False, server_default="{}"),
    *timestamps("task_state"),
)

runtime_checkpoint = Table(
    "runtime_checkpoint",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("state_version", Integer, nullable=False),
    __import__("sqlalchemy").Column("storage_uri", Text, nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("runtime_checkpoint"),
)

analysis_context = Table(
    "analysis_context",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("context_version", String(100), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("analysis_context"),
)

context_source_ref = Table(
    "context_source_ref",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "context_id",
        UUID(as_uuid=True),
        ForeignKey("analysis_context.id"),
        nullable=False,
        index=True,
    ),
    __import__("sqlalchemy").Column("source_type", String(80), nullable=False),
    __import__("sqlalchemy").Column("identifier", String(300), nullable=False),
    __import__("sqlalchemy").Column("version", String(100), nullable=False),
    __import__("sqlalchemy").Column("content_hash", String(128), nullable=False),
    *timestamps("context_source_ref"),
)

semantic_asset_ref = Table(
    "semantic_asset_ref",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "context_id",
        UUID(as_uuid=True),
        ForeignKey("analysis_context.id"),
        nullable=False,
        index=True,
    ),
    __import__("sqlalchemy").Column("asset_type", String(80), nullable=False),
    __import__("sqlalchemy").Column("asset_id", String(300), nullable=False),
    __import__("sqlalchemy").Column("version", String(100), nullable=False),
    *timestamps("semantic_asset_ref"),
)

analysis_plan = Table(
    "analysis_plan",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("context_version", String(100), nullable=False),
    __import__("sqlalchemy").Column("version", Integer, nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("analysis_plan"),
)

analysis_step = Table(
    "analysis_step",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "plan_id", UUID(as_uuid=True), ForeignKey("analysis_plan.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("ordinal", Integer, nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("analysis_step"),
)

hypothesis = Table(
    "hypothesis",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("state", String(40), nullable=False),
    __import__("sqlalchemy").Column("priority", Integer, nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("hypothesis"),
)

execution_record = Table(
    "execution_record",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("tool_name", String(200), nullable=False),
    __import__("sqlalchemy").Column("status", String(40), nullable=False),
    __import__("sqlalchemy").Column("result_hash", String(128)),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("execution_record"),
)

observation = Table(
    "observation",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column(
        "execution_id", UUID(as_uuid=True), ForeignKey("execution_record.id"), nullable=False
    ),
    __import__("sqlalchemy").Column("result_hash", String(128), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("observation"),
)

validation_result = Table(
    "validation_result",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("rule_id", String(200), nullable=False),
    __import__("sqlalchemy").Column("status", String(40), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("validation_result"),
)

claim = Table(
    "claim",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("claim_type", String(40), nullable=False),
    __import__("sqlalchemy").Column("status", String(40), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("claim"),
)

evidence = Table(
    "evidence",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column(
        "observation_id", UUID(as_uuid=True), ForeignKey("observation.id"), nullable=False
    ),
    __import__("sqlalchemy").Column(
        "execution_id", UUID(as_uuid=True), ForeignKey("execution_record.id"), nullable=False
    ),
    __import__("sqlalchemy").Column("result_hash", String(128), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("evidence"),
)

claim_evidence_link = Table(
    "claim_evidence_link",
    metadata,
    __import__("sqlalchemy").Column(
        "claim_id", UUID(as_uuid=True), ForeignKey("claim.id"), primary_key=True
    ),
    __import__("sqlalchemy").Column(
        "evidence_id", UUID(as_uuid=True), ForeignKey("evidence.id"), primary_key=True
    ),
    __import__("sqlalchemy").Column("relation", String(40), nullable=False),
    __import__("sqlalchemy").Column("rationale", Text, nullable=False),
    __import__("sqlalchemy").Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)

artifact = Table(
    "artifact",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("artifact_type", String(50), nullable=False),
    __import__("sqlalchemy").Column("content_hash", String(128), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("artifact"),
)

domain_event = Table(
    "domain_event",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), nullable=False, index=True
    ),
    __import__("sqlalchemy").Column("event_type", String(80), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    __import__("sqlalchemy").Column(
        "occurred_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)

audit_event = Table(
    "audit_event",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "task_id", UUID(as_uuid=True), ForeignKey("analysis_task.id"), index=True
    ),
    __import__("sqlalchemy").Column("actor_id", String(200), nullable=False),
    __import__("sqlalchemy").Column("action", String(200), nullable=False),
    __import__("sqlalchemy").Column("outcome", String(40), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False, server_default="{}"),
    __import__("sqlalchemy").Column(
        "occurred_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)

evaluation_case = Table(
    "evaluation_case",
    metadata,
    __import__("sqlalchemy").Column("case_id", String(20), primary_key=True),
    __import__("sqlalchemy").Column("suite_version", String(100), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("evaluation_case"),
)

evaluation_run = Table(
    "evaluation_run",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column("suite_version", String(100), nullable=False),
    __import__("sqlalchemy").Column("model_provider_version", String(200), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False, server_default="{}"),
    *timestamps("evaluation_run"),
)

evaluation_result = Table(
    "evaluation_result",
    metadata,
    id_column(),
    __import__("sqlalchemy").Column(
        "evaluation_run_id",
        UUID(as_uuid=True),
        ForeignKey("evaluation_run.id"),
        nullable=False,
        index=True,
    ),
    __import__("sqlalchemy").Column(
        "case_id", String(20), ForeignKey("evaluation_case.case_id"), nullable=False
    ),
    __import__("sqlalchemy").Column("passed", String(10), nullable=False),
    __import__("sqlalchemy").Column("payload", JSON, nullable=False),
    *timestamps("evaluation_result"),
)
