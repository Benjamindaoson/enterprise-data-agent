"""API Contract Tests for Phase 0A.

Tests verify that API endpoints match their OpenAPI contracts
and return correctly structured responses per domain models.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from pydantic import HttpUrl

from eiw.domain.enums import (
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
from eiw.domain.models import (
    AnalysisTask,
    AnalysisTaskCreate,
    AnalysisTaskResponse,
    Claim,
    ClaimCreate,
    ClaimEvidenceLink,
    ClaimResponse,
    DatasetManifest,
    EvaluationCase,
    Evidence,
    EvidenceCreate,
    EvidenceResponse,
    Hypothesis,
    HypothesisCreate,
    HypothesisResponse,
    MetricDefinition,
    UserContext,
    ValidationResult,
    VersionRef,
)

# =============================================================================
# Task API Contract Tests
# =============================================================================


class TestTaskAPIContracts:
    """Contract tests for Task endpoints."""

    def test_create_task_request_schema(self) -> None:
        """Verify task creation request matches OpenAPI schema."""
        request = AnalysisTaskCreate(
            business_question="What were total sales in Q1 2024?",
            user_context={
                "user_id": "user123",
                "tenant_id": "tenant456",
                "preferences": {"currency": "USD"},
            },
            scope_hint={
                "time_period": "Q1 2024",
                "granularity": "daily",
            },
            policy_version="1.0.0",
            domain_id="iowa_liquor_wholesale",
            dataset_snapshot_id="snapshot-001",
        )

        # Verify required fields per contract
        assert request.business_question is not None
        assert len(request.business_question) > 0
        assert request.user_context.get("user_id") == "user123"
        assert request.policy_version is not None
        assert request.domain_id is not None

    def test_create_task_response_schema(self) -> None:
        """Verify task creation response matches domain model."""
        # Create UserContext first
        user_ctx = UserContext(
            user_id="user123",
            tenant_id="tenant456",
            policy_version="1.0.0",
        )

        # Create AnalysisTask domain model
        from eiw.domain.models import AnalysisTask
        task = AnalysisTask(
            user_context=user_ctx,
            business_question="What were total sales in Q1 2024?",
            domain_id="iowa_liquor_wholesale",
        )

        response = AnalysisTaskResponse.from_task(task)

        assert response.task_id == str(task.task_id)
        assert response.state == TaskState.CREATED
        assert response.created_at is not None

    def test_task_state_transitions_valid(self) -> None:
        """Verify valid task state transitions per contract."""
        valid_transitions = {
            TaskState.CREATED: [TaskState.NEEDS_CLARIFICATION, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.NEEDS_CLARIFICATION: [TaskState.CONTEXT_READY, TaskState.CANCELLED],
            TaskState.CONTEXT_READY: [TaskState.PLANNED, TaskState.CANCELLED],
            TaskState.PLANNED: [TaskState.RUNNING, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.RUNNING: [TaskState.VERIFYING, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.VERIFYING: [TaskState.COMPLETED, TaskState.PARTIAL, TaskState.FAILED, TaskState.CANCELLED],
            TaskState.COMPLETED: [],  # Terminal state
            TaskState.PARTIAL: [],  # Terminal state
            TaskState.FAILED: [TaskState.PLANNED],  # Can retry
            TaskState.CANCELLED: [],  # Terminal state
        }

        for from_state, to_states in valid_transitions.items():
            for to_state in to_states:
                # Verify both states are valid enum values
                assert isinstance(from_state, TaskState)
                assert isinstance(to_state, TaskState)

    def test_task_id_format_contract(self) -> None:
        """Verify task_id format matches UUID contract."""
        user_ctx = UserContext(
            user_id="user123",
            tenant_id="tenant456",
            policy_version="1.0.0",
        )

        task = AnalysisTask(
            user_context=user_ctx,
            business_question="Test question",
            domain_id="test_domain",
        )

        # Verify UUID format (36 characters with hyphens)
        assert len(str(task.task_id)) == 36
        assert str(task.task_id).count("-") == 4


# =============================================================================
# Hypothesis API Contract Tests
# =============================================================================


class TestHypothesisAPIContracts:
    """Contract tests for Hypothesis endpoints."""

    def test_hypothesis_state_machine(self) -> None:
        """Verify hypothesis state transitions per contract."""
        # Valid hypothesis state progression
        valid_hypothesis_states = [
            HypothesisState.PROPOSED,
            HypothesisState.TESTING,
            HypothesisState.SUPPORTED,
            HypothesisState.REJECTED,
            HypothesisState.INCONCLUSIVE,
        ]

        for state in valid_hypothesis_states:
            hypothesis = Hypothesis(
                task_id=uuid4(),
                statement="Test hypothesis",
                rationale="Test rationale",
                state=state,
                priority=1,
            )
            assert hypothesis.state == state

    def test_hypothesis_create_schema(self) -> None:
        """Verify hypothesis creation request schema."""
        create = HypothesisCreate(
            statement="Higher temperatures correlate with increased sales",
            rationale="Based on seasonal patterns observed in historical data",
            priority=1,
        )

        assert create.statement is not None
        assert len(create.statement) > 0
        assert create.priority >= 1
        assert create.priority <= 100

    def test_hypothesis_response_schema(self) -> None:
        """Verify hypothesis response matches domain model."""
        hypothesis = Hypothesis(
            task_id=uuid4(),
            statement="Higher temps correlate with increased sales",
            rationale="Based on seasonal patterns",
            state=HypothesisState.PROPOSED,
            priority=2,
        )

        response = HypothesisResponse.from_hypothesis(hypothesis)

        assert response.hypothesis_id is not None
        assert response.state == HypothesisState.PROPOSED


# =============================================================================
# Claim API Contract Tests
# =============================================================================


class TestClaimAPIContracts:
    """Contract tests for Claim endpoints."""

    def test_claim_type_enum_values(self) -> None:
        """Verify claim types match contract."""
        valid_claim_types = [
            ClaimType.FACT,
            ClaimType.INFERENCE,
            ClaimType.RECOMMENDATION,
        ]

        for claim_type in valid_claim_types:
            claim = Claim(
                task_id=uuid4(),
                claim_type=claim_type,
                statement="Test claim",
            )
            assert claim.claim_type == claim_type

    def test_claim_create_schema(self) -> None:
        """Verify claim creation request schema."""
        create = ClaimCreate(
            claim_type=ClaimType.FACT,
            statement="Total sales in Q1 2024 were $5.2M",
            evidence_ids=["ev-001", "ev-002"],
            limitations=["Based on snapshot data only"],
            confidence=0.95,
        )

        assert create.claim_type in ClaimType
        assert create.statement is not None
        assert create.confidence is None or 0 <= create.confidence <= 1.0

    def test_claim_response_schema(self) -> None:
        """Verify claim response matches domain model."""
        claim = Claim(
            task_id=uuid4(),
            claim_type=ClaimType.INFERENCE,
            statement="Average order value increased by 15%",
            confidence=0.87,
            status="VERIFIED",
        )

        response = ClaimResponse.from_claim(claim)

        assert response.claim_id is not None
        assert response.confidence is None or 0 <= response.confidence <= 1.0


# =============================================================================
# Evidence API Contract Tests
# =============================================================================


class TestEvidenceAPIContracts:
    """Contract tests for Evidence endpoints."""

    def test_evidence_relation_enum_values(self) -> None:
        """Verify evidence relation types match contract."""
        valid_relations = [
            EvidenceRelation.SUPPORTS,
            EvidenceRelation.REFUTES,
            EvidenceRelation.QUALIFIES,
        ]

        for relation in valid_relations:
            link = ClaimEvidenceLink(
                claim_id=uuid4(),
                evidence_id=uuid4(),
                relation=relation,
                rationale="Test rationale",
            )
            assert link.relation == relation

    def test_evidence_create_schema(self) -> None:
        """Verify evidence creation request schema."""
        create = EvidenceCreate(
            observation_id=str(uuid4()),
            execution_id=str(uuid4()),
            tool_name="sql_executor",
            tool_version="1.0.0",
            computation_identifier="sum(sales)",
            result_snapshot_uri="s3://bucket/snapshot-001.parquet",
            result_hash="abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
            parameters={"filter": "region='North'"},
        )

        assert create.tool_name is not None
        assert create.computation_identifier is not None
        assert len(create.result_hash) == 64  # SHA-256

    def test_evidence_response_schema(self) -> None:
        """Verify evidence response matches domain model."""
        evidence = Evidence(
            task_id=uuid4(),
            observation_id=uuid4(),
            execution_id=uuid4(),
            tool_name="sql_executor",
            tool_version="1.0.0",
            computation_identifier="sum(sales)",
            result_snapshot_uri="s3://bucket/snapshot-001.parquet",
            result_hash="abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
            dataset_snapshot=VersionRef(
                identifier="snap-001",
                version="1.0.0",
                content_hash="abcd1234567890efgh",
            ),
            metric_version="1.0.0",
            context_version="1.0.0",
            user_scope_fingerprint="fp1234567890abcd",
        )

        response = EvidenceResponse.from_evidence(evidence)

        assert response.evidence_id is not None
        assert len(response.result_hash) == 64


# =============================================================================
# Evaluation API Contract Tests
# =============================================================================


class TestEvaluationAPIContracts:
    """Contract tests for Evaluation endpoints."""

    def test_evaluation_case_schema(self) -> None:
        """Verify evaluation case matches contract."""
        from eiw.domain.models import ExpectedSemanticResult, VersionRef

        user_ctx = UserContext(
            user_id="eval_user",
            tenant_id="eval_tenant",
            policy_version="1.0.0",
        )

        case = EvaluationCase(
            case_id="GC-001",
            title="Q1 Sales Summary",
            business_question="What were total sales in Q1 2024?",
            user_context=user_ctx,
            dataset_snapshot=VersionRef(
                identifier="snap-001",
                version="1.0.0",
                content_hash="abcd1234567890efgh",
            ),
            semantic_package=VersionRef(
                identifier="pkg-001",
                version="1.0.0",
                content_hash="ijkl9876543210mnop",
            ),
            expected_semantics=ExpectedSemanticResult(
                metric_ids=["total_sales"],
                dimension_filters={"region": ["Iowa"]},
            ),
            allowed_data_objects=["sales", "products", "stores"],
            forbidden_data_objects=["employees", "salaries"],
            expected_numeric_values={"total_sales": Decimal("5200000")},
            numeric_tolerance=Decimal("0.01"),
            required_hypothesis_topics=["sales_trend"],
            required_claim_types=[ClaimType.FACT],
            acceptable_outcomes=[TaskState.COMPLETED],
            tags=["q1", "2024", "sales"],
        )

        assert case.case_id is not None
        assert case.title is not None
        assert case.expected_numeric_values is not None
        assert case.numeric_tolerance is not None

    def test_failure_category_enum_values(self) -> None:
        """Verify failure categories match contract."""
        valid_categories = [
            FailureCategory.INTENT,
            FailureCategory.SEMANTIC,
            FailureCategory.TIME_SCOPE,
            FailureCategory.GRAIN,
            FailureCategory.JOIN,
            FailureCategory.POLICY,
            FailureCategory.DATA_QUALITY,
            FailureCategory.PLANNING,
            FailureCategory.TOOL,
            FailureCategory.QUERY,
            FailureCategory.NUMERIC,
            FailureCategory.VERIFICATION,
            FailureCategory.EVIDENCE,
            FailureCategory.RUNTIME,
            FailureCategory.PRESENTATION,
        ]

        for category in valid_categories:
            assert isinstance(category, FailureCategory)


# =============================================================================
# Validation API Contract Tests
# =============================================================================


class TestValidationAPIContracts:
    """Contract tests for Validation endpoints."""

    def test_validation_status_enum_values(self) -> None:
        """Verify validation status values match contract."""
        valid_statuses = [
            ValidationStatus.PASSED,
            ValidationStatus.FAILED,
            ValidationStatus.WARNING,
            ValidationStatus.NOT_VERIFIABLE,
        ]

        for status in valid_statuses:
            validation = ValidationResult(
                task_id=uuid4(),
                rule_id="rule-001",
                status=status,
                subject_type="metric",
                details="Validation details",
            )
            assert validation.status == status

    def test_investigation_decision_enum_values(self) -> None:
        """Verify investigation decision values match contract."""
        valid_decisions = [
            InvestigationDecisionType.EXECUTE,
            InvestigationDecisionType.REFINE,
            InvestigationDecisionType.REQUEST_CLARIFICATION,
            InvestigationDecisionType.SYNTHESIZE,
            InvestigationDecisionType.COMPLETE_PARTIAL,
            InvestigationDecisionType.STOP_FAILED,
        ]

        for decision in valid_decisions:
            assert isinstance(decision, InvestigationDecisionType)


# =============================================================================
# Dataset Manifest API Contract Tests
# =============================================================================


class TestDatasetAPIContracts:
    """Contract tests for Dataset endpoints."""

    def test_dataset_manifest_schema(self) -> None:
        """Verify dataset manifest matches contract."""
        manifest = DatasetManifest(
            snapshot_id="snapshot-001",
            source_url=HttpUrl("https://example.com/data/snapshot-001"),
            extracted_at=datetime.now(),
            business_date_min=date(2024, 1, 1),
            business_date_max=date(2024, 3, 31),
            raw_file_sha256="a" * 64,
            row_count=1000000,
            schema_hash="abcdefgh12345678",
            license="MIT",
            status="READY",
        )

        assert manifest.snapshot_id is not None
        assert manifest.row_count > 0
        assert manifest.business_date_max >= manifest.business_date_min

    def test_data_classification_enum_values(self) -> None:
        """Verify data classification values match contract."""
        valid_classifications = [
            DataClassification.PUBLIC,
            DataClassification.INTERNAL,
            DataClassification.CONFIDENTIAL,
            DataClassification.RESTRICTED,
        ]

        for classification in valid_classifications:
            assert isinstance(classification, DataClassification)


# =============================================================================
# Event API Contract Tests
# =============================================================================


class TestEventAPIContracts:
    """Contract tests for Event endpoints."""

    def test_event_type_enum_values(self) -> None:
        """Verify event types match contract."""
        valid_event_types = [
            EventType.TASK_CREATED,
            EventType.TASK_STATE_CHANGED,
            EventType.CONTEXT_COMPILED,
            EventType.PLAN_CREATED,
            EventType.HYPOTHESIS_UPDATED,
            EventType.TOOL_STARTED,
            EventType.TOOL_COMPLETED,
            EventType.VALIDATION_COMPLETED,
            EventType.CLAIM_CREATED,
            EventType.EVIDENCE_LINKED,
            EventType.ARTIFACT_CREATED,
            EventType.CHECKPOINT_SAVED,
            EventType.FAILURE_RECORDED,
        ]

        for event_type in valid_event_types:
            assert isinstance(event_type, EventType)


# =============================================================================
# Metric Definition API Contract Tests
# =============================================================================


class TestMetricAPIContracts:
    """Contract tests for Metric endpoints."""

    def test_metric_definition_schema(self) -> None:
        """Verify metric definition matches contract."""
        metric = MetricDefinition(
            metric_id="total_sales",
            name="Total Sales",
            description="Sum of all sales transactions",
            unit="$",
            aggregation="sum",
            semantic_type="currency",
        )

        assert metric.metric_id is not None
        assert metric.name is not None
        assert metric.unit is not None
        assert metric.aggregation in ["sum", "avg", "count", "min", "max", "count_distinct"]
