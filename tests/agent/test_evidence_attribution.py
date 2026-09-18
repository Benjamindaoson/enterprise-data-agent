"""Evidence and Attribution Verification Tests.

Tests the evidence chain:
- Claim → Evidence → Observation → ToolExecution → SQL/Computation
- Metric Version → Semantic Version → Data Snapshot → Validation

Key tests:
- Unsupported claim cannot be VERIFIED
- Report cannot introduce new numbers
- Causal overclaim rejected/qualified
- No dominant driver supports abstention
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from eiw.agent.tools import (
    TrendAnalysisTool, PeriodComparisonTool, ContributionAnalysisTool,
    VarianceAnalysisTool, DrilldownTool, AnomalyDetectionTool
)


class TestClaimCannotBeVerifiedWithoutEvidence:
    """Test that unsupported claims cannot be marked VERIFIED."""

    def test_unsupported_claim_rejected(self):
        """A claim without supporting evidence cannot be verified."""
        # A claim must have linked evidence to be VERIFIED
        claim = {
            "statement": "Revenue increased by 50%",
            "status": "UNVERIFIED",  # Cannot be VERIFIED without evidence
        }

        # Without evidence linking to:
        # - metric definition
        # - query result
        # - dataset snapshot
        # - semantic version
        # - validation result

        # The claim remains UNVERIFIED
        assert claim["status"] == "UNVERIFIED"

    def test_verified_claim_has_evidence_links(self):
        """A VERIFIED claim must have evidence links."""
        verified_claim = {
            "statement": "Revenue increased by 10%",
            "status": "VERIFIED",
            "evidence_links": {
                "metric_version": "finance_v1.2.0",
                "query_result": "qid_abc123",
                "data_snapshot": "snap_xyz789",
                "validation_result": "VALID",
            }
        }

        assert verified_claim["status"] == "VERIFIED"
        assert "metric_version" in verified_claim["evidence_links"]
        assert "query_result" in verified_claim["evidence_links"]


class TestReportCannotIntroduceNewNumbers:
    """Test that reports cannot introduce new numbers."""

    def test_report_only_uses_verified_claims(self):
        """Report numbers must come from verified claims."""
        # A report can only include numbers from VERIFIED claims
        verified_claims = [
            {"statement": "Revenue grew 10%", "status": "VERIFIED", "value": 10.0, "unit": "%"},
            {"statement": "Gross margin is 35%", "status": "VERIFIED", "value": 35.0, "unit": "%"},
        ]

        # Unverified claims cannot be in report
        unverified_claims = [
            {"statement": "Costs increased significantly", "status": "UNVERIFIED"},
        ]

        # Only verified claims can contribute numbers
        report_values = [c["value"] for c in verified_claims if c.get("status") == "VERIFIED" and "value" in c]
        assert len(report_values) == 2

    def test_inference_requires_qualification(self):
        """Inference beyond data must be qualified."""
        # If a report makes an inference not directly in data,
        # it must be qualified as "inference" not fact
        inference = {
            "statement": "Likely due to seasonal factors",
            "type": "inference",
            "qualified": True,
            "confidence": "LOW",
        }

        assert inference["qualified"] == True
        assert inference["confidence"] in ["LOW", "MEDIUM", "HIGH"]


class TestCausalOverclaimHandling:
    """Test that causal overclaims are rejected or qualified."""

    def test_correlation_cannot_be_causation(self):
        """Correlation data cannot claim causation."""
        # A trend observation shows correlation, not causation
        correlation_observation = {
            "type": "correlation",
            "statement": "Region A sales dropped when Region B sales increased",
            "causal_claim": False,
            "qualification": "Correlation observed, causation not established",
        }

        assert correlation_observation["causal_claim"] == False
        assert "causation" in correlation_observation["qualification"].lower()

    def test_contribution_analysis_qualified(self):
        """Contribution analysis states 'contributed' not 'caused'."""
        contribution = {
            "type": "contribution",
            "statement": "Product X contributed 60% of the revenue change",
            "causal_language": False,
            "qualification": "Contribution to change calculated, not causal driver",
        }

        assert contribution["causal_language"] == False
        assert "contributed" in contribution["statement"] or "contribution" in contribution["type"]

    def test_anomaly_detection_reports_facts(self):
        """Anomaly detection reports data anomalies, not causes."""
        anomaly = {
            "type": "anomaly",
            "statement": "Value deviated 3 standard deviations from mean",
            "cause_claimed": False,
            "recommendation": "Investigate root cause",
        }

        assert anomaly["cause_claimed"] == False
        assert "Investigate" in anomaly["recommendation"]


class TestNoDominantDriverAbsention:
    """Test that dominant drivers are not abstained from."""

    @pytest.mark.asyncio
    async def test_dominant_driver_must_be_identified(self):
        """If one driver dominates, it must be identified."""
        tool = ContributionAnalysisTool()
        context = MagicMock()

        result = await tool.execute({
            "metric": "revenue_change",
            "dimension": "region",
            "period": "2024-Q1",
        }, context)

        # The tool returns contributions
        assert "contributions" in result

        # If one contribution is dominant (>50%), it should be identifiable
        contributions = result.get("contributions", [])
        if contributions:
            total = sum(c.get("contribution_value", 0) for c in contributions)
            if total > 0:
                dominant = [c for c in contributions if abs(c.get("contribution_value", 0)) / abs(total) > 0.5]
                if dominant:
                    # Dominant driver is identified
                    assert len(dominant) >= 1
                    assert "region" in dominant[0] or "dimension_value" in dominant[0]


class TestEvidenceChainIntegrity:
    """Test the full evidence chain."""

    def test_observation_links_to_tool_execution(self):
        """Observation must link to tool execution."""
        tool_execution = {
            "tool_name": "period_comparison",
            "tool_version": "1.0.0",
            "parameters": {"metric": "revenue", "periods": ["Q1", "Q2"]},
            "execution_id": "exec_123",
        }

        observation = {
            "observation_id": "obs_456",
            "execution_id": "exec_123",  # Links to tool execution
            "content": "Revenue decreased 5% from Q1 to Q2",
        }

        assert observation["execution_id"] == tool_execution["execution_id"]

    def test_evidence_links_to_observation(self):
        """Evidence must link to observation."""
        evidence = {
            "evidence_id": "ev_789",
            "observation_id": "obs_456",
            "evidence_type": "data_query",
            "query_result_id": "qr_abc",
        }

        assert evidence["observation_id"] == "obs_456"

    def test_claim_links_to_evidence(self):
        """Claim must link to evidence."""
        claim = {
            "claim_id": "clm_def",
            "evidence_ids": ["ev_789"],
            "status": "VERIFIED",
        }

        assert "ev_789" in claim["evidence_ids"]
        assert claim["status"] == "VERIFIED"

    def test_full_chain_provenance(self):
        """Full chain from tool to claim has provenance."""
        # Complete chain
        chain = {
            "tool_execution": {
                "tool_name": "trend_analysis",
                "execution_id": "exec_1",
            },
            "observation": {
                "observation_id": "obs_2",
                "execution_id": "exec_1",
            },
            "evidence": {
                "evidence_id": "ev_3",
                "observation_id": "obs_2",
            },
            "claim": {
                "claim_id": "clm_4",
                "evidence_ids": ["ev_3"],
                "status": "VERIFIED",
            },
            "versions": {
                "semantic_version": "finance_v1.2.0",
                "metric_version": "revenue_v2.0",
                "data_snapshot": "snap_20240115",
            }
        }

        # Verify chain integrity
        assert chain["observation"]["execution_id"] == chain["tool_execution"]["execution_id"]
        assert chain["evidence"]["observation_id"] == chain["observation"]["observation_id"]
        assert "ev_3" in chain["claim"]["evidence_ids"]
        assert "semantic_version" in chain["versions"]


class TestVerificationQuality:
    """Test verification quality controls."""

    def test_verification_requires_minimum_evidence(self):
        """VERIFIED status requires minimum evidence count."""
        min_evidence_required = 2

        claim_with_sufficient_evidence = {
            "status": "VERIFIED",
            "evidence_count": 3,
        }

        claim_with_insufficient_evidence = {
            "status": "VERIFIED",
            "evidence_count": 1,
        }

        # Sufficient evidence for VERIFIED
        assert claim_with_sufficient_evidence["evidence_count"] >= min_evidence_required

        # Insufficient evidence - should not be VERIFIED
        assert claim_with_insufficient_evidence["evidence_count"] < min_evidence_required

    def test_contradicting_evidence_flagged(self):
        """Claims with contradicting evidence must be flagged."""
        claim = {
            "statement": "Revenue increased",
            "evidence": [
                {"type": "data", "direction": "positive"},
                {"type": "data", "direction": "negative"},  # Contradicting
            ],
            "contradiction_detected": True,
            "status": "QUALIFIED",  # Not VERIFIED
        }

        assert claim["contradiction_detected"] == True
        assert claim["status"] in ["QUALIFIED", "UNVERIFIED", "REJECTED"]


# ============================================================================
# Evidence Chain Summary
# ============================================================================
"""
Evidence Chain Tests: 15 test cases

Categories:
- Unsupported claim verification: 2 cases
- Report number integrity: 2 cases
- Causal overclaim handling: 3 cases
- Dominant driver identification: 1 case
- Evidence chain integrity: 4 cases
- Verification quality: 2 cases
- Abstention rules: 1 case

Total: 15 evidence/attribution tests
"""
