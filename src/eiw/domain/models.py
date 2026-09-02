"""Versioned, framework-independent domain models.

These objects intentionally have no dependency on FastAPI, SQLAlchemy, LangGraph,
or a model provider. They are the contracts persisted and replayed by the system.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from eiw.domain.enums import (
    ArtifactType,
    ClaimType,
    DataClassification,
    EventType,
    EvidenceRelation,
    FailureCategory,
    HypothesisState,
    InvestigationDecisionType,
    TaskState,
    ValidationStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


EntityId = UUID
Money = Annotated[Decimal, Field(max_digits=20, decimal_places=4)]


class DomainModel(BaseModel):
    """Common serialization and forward-compatible contract settings."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=False)


class VersionRef(DomainModel):
    identifier: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    content_hash: str = Field(min_length=16, max_length=128)


class UserContext(DomainModel):
    user_id: str = Field(min_length=1, max_length=200)
    tenant_id: str = Field(min_length=1, max_length=200)
    roles: list[str] = Field(default_factory=list)
    policy_version: str = Field(min_length=1, max_length=100)
    allowed_metric_ids: list[str] = Field(default_factory=list)
    allowed_dimension_ids: list[str] = Field(default_factory=list)
    data_classification_ceiling: DataClassification = DataClassification.INTERNAL


class TaskScopeHint(DomainModel):
    metric_hints: list[str] = Field(default_factory=list)
    dimension_filters: dict[str, list[str]] = Field(default_factory=dict)
    start_date: date | None = None
    end_date: date | None = None
    comparison_start_date: date | None = None
    comparison_end_date: date | None = None
    grain: str | None = None


class TaskBudget(DomainModel):
    max_query_count: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=20, ge=1, le=200)
    max_investigation_depth: int = Field(default=4, ge=1, le=12)
    max_runtime_seconds: int = Field(default=180, ge=10, le=3600)
    max_result_rows: int = Field(default=5000, ge=1, le=100_000)


class ClarificationRequest(DomainModel):
    clarification_id: EntityId = Field(default_factory=uuid4)
    question: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=2000)
    blocking_fields: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ClarificationResponse(DomainModel):
    clarification_id: EntityId
    response: str = Field(min_length=1, max_length=4000)
    responded_at: datetime = Field(default_factory=utc_now)


class TaskLineage(DomainModel):
    parent_task_id: EntityId | None = None
    reused_evidence_ids: list[EntityId] = Field(default_factory=list)
    parent_context_version: str | None = None


class RuntimeCheckpointRef(DomainModel):
    checkpoint_id: EntityId = Field(default_factory=uuid4)
    state_version: int = Field(ge=1)
    storage_uri: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class AnalysisTask(DomainModel):
    task_id: EntityId = Field(default_factory=uuid4)
    idempotency_key: str | None = Field(default=None, max_length=200)
    user_context: UserContext
    domain_id: str = Field(min_length=1, max_length=200)
    business_question: str = Field(min_length=3, max_length=5000)
    scope_hint: TaskScopeHint = Field(default_factory=TaskScopeHint)
    budget: TaskBudget = Field(default_factory=TaskBudget)
    state: TaskState = TaskState.CREATED
    lineage: TaskLineage = Field(default_factory=TaskLineage)
    context_version: str | None = None
    semantic_package_version: str | None = None
    dataset_snapshot: VersionRef | None = None
    clarification_requests: list[ClarificationRequest] = Field(default_factory=list)
    clarification_responses: list[ClarificationResponse] = Field(default_factory=list)
    runtime_checkpoint: RuntimeCheckpointRef | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def completed_state_requires_completion_time(self) -> "AnalysisTask":
        terminal = {TaskState.COMPLETED, TaskState.PARTIAL, TaskState.FAILED, TaskState.CANCELLED}
        if self.state in terminal and self.completed_at is None:
            raise ValueError("terminal task states require completed_at")
        return self


class ResolvedMetric(DomainModel):
    metric_id: str
    confidence: float = Field(ge=0, le=1)
    interpretation: str


class ResolvedBusinessIntent(DomainModel):
    objective: str
    metrics: list[ResolvedMetric] = Field(min_length=1)
    dimension_filters: dict[str, list[str]] = Field(default_factory=dict)
    primary_period_start: date | None = None
    primary_period_end: date | None = None
    comparison_period_start: date | None = None
    comparison_period_end: date | None = None
    requested_grain: str | None = None
    ambiguities: list[str] = Field(default_factory=list)
    requires_clarification: bool = False


class ContextSourceRef(DomainModel):
    source_type: Literal[
        "semantic_package", "catalog", "policy", "dataset_manifest", "business_rule"
    ]
    identifier: str
    version: str
    content_hash: str


class SemanticAssetRef(DomainModel):
    asset_type: Literal["metric", "dimension", "join_policy", "business_rule", "quality_rule"]
    asset_id: str
    version: str


class DataAvailability(DomainModel):
    metric_id: str
    available_from: date | None = None
    available_to: date | None = None
    status: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE"]
    note: str | None = None


class AnalysisContext(DomainModel):
    context_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    context_version: str
    resolved_intent: ResolvedBusinessIntent
    user_context: UserContext
    dataset_snapshot: VersionRef
    semantic_package: VersionRef
    source_refs: list[ContextSourceRef]
    semantic_assets: list[SemanticAssetRef]
    allowed_data_objects: list[str]
    allowed_join_paths: list[str]
    available_tools: list[str]
    data_availability: list[DataAvailability] = Field(default_factory=list)
    quality_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceRequirement(DomainModel):
    description: str
    required_validation_rules: list[str] = Field(default_factory=list)


class AnalysisStep(DomainModel):
    step_id: EntityId = Field(default_factory=uuid4)
    ordinal: int = Field(ge=1)
    title: str
    purpose: str
    depends_on_step_ids: list[EntityId] = Field(default_factory=list)
    candidate_hypothesis_ids: list[EntityId] = Field(default_factory=list)
    allowed_tools: list[str] = Field(min_length=1)
    expected_outputs: list[str] = Field(min_length=1)
    evidence_requirements: list[EvidenceRequirement] = Field(default_factory=list)
    stop_if: list[str] = Field(default_factory=list)


class AnalysisPlan(DomainModel):
    plan_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    context_version: str
    business_objective: str
    completion_criteria: list[str] = Field(min_length=1)
    clarification_conditions: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    steps: list[AnalysisStep] = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def step_ordinals_are_unique(self) -> "AnalysisPlan":
        ordinals = [step.ordinal for step in self.steps]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("analysis plan step ordinals must be unique")
        return self


class Hypothesis(DomainModel):
    hypothesis_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    statement: str
    rationale: str
    state: HypothesisState = HypothesisState.PROPOSED
    priority: int = Field(default=50, ge=1, le=100)
    required_observation_types: list[str] = Field(default_factory=list)
    evidence_ids: list[EntityId] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InvestigationDecision(DomainModel):
    decision_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    decision_type: InvestigationDecisionType
    rationale_summary: str
    target_step_id: EntityId | None = None
    target_hypothesis_ids: list[EntityId] = Field(default_factory=list)
    budget_remaining: TaskBudget
    created_at: datetime = Field(default_factory=utc_now)


class ToolExecutionRequest(DomainModel):
    request_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    step_id: EntityId | None = None
    tool_name: str
    tool_version: str
    input_parameters: dict[str, Any] = Field(default_factory=dict)
    context_version: str
    requested_by: str = "analytical_orchestrator"


class ExecutionRecord(DomainModel):
    execution_id: EntityId = Field(default_factory=uuid4)
    request_id: EntityId
    task_id: EntityId
    tool_name: str
    tool_version: str
    status: Literal["SUCCEEDED", "FAILED", "CANCELLED"]
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    result_row_count: int | None = Field(default=None, ge=0)
    result_hash: str | None = None
    policy_checks: list[str] = Field(default_factory=list)
    error_category: FailureCategory | None = None
    error_summary: str | None = None


class Observation(DomainModel):
    observation_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    execution_id: EntityId
    observation_type: str
    statement: str
    numeric_values: dict[str, Money] = Field(default_factory=dict)
    dimensions: dict[str, str] = Field(default_factory=dict)
    result_snapshot_uri: str
    result_hash: str
    data_freshness_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ValidationResult(DomainModel):
    validation_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    rule_id: str
    status: ValidationStatus
    subject_type: str
    subject_id: EntityId | None = None
    details: str
    expected: str | None = None
    actual: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Claim(DomainModel):
    claim_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    claim_type: ClaimType
    statement: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)
    status: Literal["DRAFT", "VERIFIED", "QUALIFIED", "REJECTED"] = "DRAFT"
    created_at: datetime = Field(default_factory=utc_now)


class Evidence(DomainModel):
    evidence_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    observation_id: EntityId
    execution_id: EntityId
    tool_name: str
    tool_version: str
    computation_identifier: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    result_snapshot_uri: str
    result_hash: str
    dataset_snapshot: VersionRef
    metric_version: str
    context_version: str
    user_scope_fingerprint: str
    data_freshness_at: datetime | None = None
    validation_ids: list[EntityId] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ClaimEvidenceLink(DomainModel):
    claim_id: EntityId
    evidence_id: EntityId
    relation: EvidenceRelation
    rationale: str
    created_at: datetime = Field(default_factory=utc_now)


class Artifact(DomainModel):
    artifact_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    artifact_type: ArtifactType
    uri: str
    content_hash: str
    claim_ids: list[EntityId] = Field(default_factory=list)
    evidence_ids: list[EntityId] = Field(default_factory=list)
    classification: DataClassification
    created_at: datetime = Field(default_factory=utc_now)


class TraceRef(DomainModel):
    trace_id: str
    span_id: str | None = None
    event_count: int = Field(default=0, ge=0)


class DomainEvent(DomainModel):
    event_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utc_now)
    trace_ref: TraceRef | None = None


class AuditEvent(DomainModel):
    audit_event_id: EntityId = Field(default_factory=uuid4)
    task_id: EntityId | None = None
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    policy_version: str
    outcome: Literal["ALLOWED", "DENIED", "ERROR"]
    occurred_at: datetime = Field(default_factory=utc_now)


class ExpectedSemanticResult(DomainModel):
    metric_ids: list[str] = Field(default_factory=list)
    dimension_filters: dict[str, list[str]] = Field(default_factory=dict)
    primary_period_start: date | None = None
    primary_period_end: date | None = None
    comparison_period_start: date | None = None
    comparison_period_end: date | None = None
    requested_grain: str | None = None
    must_request_clarification: bool = False


class EvaluationCase(DomainModel):
    case_id: str = Field(pattern=r"^GC-\d{3}$")
    title: str
    business_question: str
    user_context: UserContext
    dataset_snapshot: VersionRef
    semantic_package: VersionRef
    expected_semantics: ExpectedSemanticResult
    allowed_data_objects: list[str] = Field(default_factory=list)
    forbidden_data_objects: list[str] = Field(default_factory=list)
    expected_numeric_values: dict[str, Money] = Field(default_factory=dict)
    numeric_tolerance: Decimal = Decimal("0.01")
    required_hypothesis_topics: list[str] = Field(default_factory=list)
    required_claim_types: list[ClaimType] = Field(default_factory=list)
    required_evidence_count: int = Field(default=0, ge=0)
    acceptable_outcomes: list[TaskState] = Field(default_factory=lambda: [TaskState.COMPLETED])
    tags: list[str] = Field(default_factory=list)


class EvaluationRun(DomainModel):
    evaluation_run_id: EntityId = Field(default_factory=uuid4)
    suite_version: str
    git_revision: str | None = None
    model_provider_version: str
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class EvaluationResult(DomainModel):
    result_id: EntityId = Field(default_factory=uuid4)
    evaluation_run_id: EntityId
    case_id: str
    passed: bool
    failure_categories: list[FailureCategory] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DatasetManifest(DomainModel):
    """Immutable data snapshot metadata; a rolling alias never substitutes for this."""

    snapshot_id: str
    source_url: HttpUrl
    extracted_at: datetime
    source_last_updated_at: datetime | None = None
    business_date_min: date
    business_date_max: date
    raw_file_sha256: str = Field(min_length=64, max_length=64)
    curated_file_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    row_count: int = Field(ge=0)
    schema_hash: str = Field(min_length=16, max_length=128)
    license: str
    status: Literal[
        "DISCOVERED",
        "INGESTING",
        "RAW_CAPTURED",
        "PROFILING",
        "CURATING",
        "VALIDATING",
        "BENCHMARKING",
        "READY",
        "REJECTED",
    ]

    @field_validator("business_date_max")
    @classmethod
    def valid_date_range(cls, value: date, info: Any) -> date:
        start = info.data.get("business_date_min")
        if isinstance(start, date) and value < start:
            raise ValueError("business_date_max cannot precede business_date_min")
        return value
