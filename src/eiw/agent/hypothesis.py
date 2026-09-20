"""Hypothesis Manager for Enterprise Data Agent.

Manages investigation hypotheses throughout the analysis lifecycle:
- Creation of initial hypotheses based on intent
- Update with observations
- State tracking
- Resolution
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from eiw.agent.intent_resolver import IntentResult, IntentType


class HypothesisState(Enum):
    """States of a hypothesis."""

    PROPOSED = "proposed"       # Initial state
    TESTING = "testing"          # Being tested
    SUPPORTED = "supported"     # Evidence supports hypothesis
    REJECTED = "rejected"       # Evidence contradicts hypothesis
    QUALIFIED = "qualified"      # Partially supported with caveats
    UNRESOLVED = "unresolved"    # Cannot be determined


@dataclass
class Hypothesis:
    """An investigation hypothesis."""

    hypothesis_id: str
    task_id: str
    topic: str
    statement: str
    rationale: str
    state: HypothesisState = HypothesisState.PROPOSED
    priority: int = 50  # 1-100
    evidence_ids: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_resolved(self) -> bool:
        """Check if hypothesis has been resolved."""
        return self.state in (
            HypothesisState.SUPPORTED,
            HypothesisState.REJECTED,
            HypothesisState.QUALIFIED,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hypothesis_id": self.hypothesis_id,
            "task_id": self.task_id,
            "topic": self.topic,
            "statement": self.statement,
            "rationale": self.rationale,
            "state": self.state.value,
            "priority": self.priority,
            "evidence_ids": self.evidence_ids,
            "observations": self.observations,
            "limitations": self.limitations,
            "confidence": self.confidence,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class HypothesisManager:
    """Manages hypotheses throughout an investigation.

    The manager:
    1. Creates initial hypotheses based on business question
    2. Tracks hypothesis state as observations come in
    3. Resolves hypotheses based on evidence
    4. Ranks hypotheses by priority
    """

    # Topic generators for different intent types
    INTENT_TOPICS: dict[IntentType, list[dict[str, str]]] = {
        IntentType.METRIC_QUERY: [
            {"topic": "metric_value", "statement": "The metric value is {value}", "rationale": "User requested the metric value"},
        ],
        IntentType.TREND_ANALYSIS: [
            {"topic": "trend_direction", "statement": "The metric shows a {direction} trend", "rationale": "Trend analysis requested"},
            {"topic": "seasonality", "statement": "The metric exhibits seasonal patterns", "rationale": "Historical data available"},
        ],
        IntentType.COMPARISON: [
            {"topic": "period_change", "statement": "The metric changed by {change}% between periods", "rationale": "Period comparison requested"},
            {"topic": "improvement", "statement": "The metric improved from prior period", "rationale": "Comparison shows positive change"},
            {"topic": "decline", "statement": "The metric declined from prior period", "rationale": "Comparison shows negative change"},
        ],
        IntentType.CONTRIBUTION: [
            {"topic": "top_contributor", "statement": "{entity} was the largest contributor to the change", "rationale": "Contribution analysis requested"},
            {"topic": "concentration", "statement": "Change is concentrated in top N entities", "rationale": "Multiple entities show significant change"},
            {"topic": "quantity_driver", "statement": "Volume change was the primary driver", "rationale": "Both quantity and price components exist"},
            {"topic": "price_driver", "statement": "Price change was the primary driver", "rationale": "Price change explains most variance"},
        ],
        IntentType.ATTRIBUTION: [
            {"topic": "root_cause", "statement": "{entity} caused the observed change", "rationale": "Attribution analysis requested"},
            {"topic": "no_single_cause", "statement": "No single factor explains the change", "rationale": "Multiple contributing factors identified"},
            {"topic": "external_factor", "statement": "External factors contributed to the change", "rationale": "Internal factors do not fully explain change"},
        ],
        IntentType.ANOMALY_DETECTION: [
            {"topic": "anomaly_exists", "statement": "An anomaly was detected in the data", "rationale": "Anomaly detection requested"},
            {"topic": "anomaly_explained", "statement": "The anomaly has a business explanation", "rationale": "Investigation of anomaly"},
            {"topic": "data_quality", "statement": "The anomaly is due to data quality issues", "rationale": "Investigation suggests data problem"},
        ],
        IntentType.BUDGET_VARIANCE: [
            {"topic": "favorable_variance", "statement": "Actual performance exceeded budget", "rationale": "Budget variance analysis"},
            {"topic": "unfavorable_variance", "statement": "Actual performance missed budget", "rationale": "Budget variance analysis"},
            {"topic": "volume_driven", "statement": "Variance was driven by volume changes", "rationale": "Mix analysis available"},
            {"topic": "price_driven", "statement": "Variance was driven by price changes", "rationale": "Mix analysis available"},
        ],
        IntentType.drilldown: [
            {"topic": "significant_breakdown", "statement": "{dimension} shows significant variation", "rationale": "Drilldown analysis requested"},
            {"topic": "uniform", "statement": "No significant variation across {dimension}", "rationale": "Drilldown shows uniform values"},
        ],
    }

    def __init__(self) -> None:
        """Initialize hypothesis manager."""
        self._hypotheses: dict[str, Hypothesis] = {}

    def create_hypotheses(
        self,
        task_id: str,
        intent: IntentResult,
    ) -> list[Hypothesis]:
        """Create initial hypotheses based on resolved intent.

        Args:
            task_id: Task identifier
            intent: Resolved business intent

        Returns:
            List of initial hypotheses
        """
        hypotheses: list[Hypothesis] = []
        intent_type = intent.intent_type

        # Get topic templates for this intent type
        templates = self.INTENT_TOPICS.get(intent_type, [])

        # Also add generic hypotheses based on metrics
        if intent.primary_metrics:
            metric = intent.primary_metrics[0]
            metric_hyp = Hypothesis(
                hypothesis_id=str(uuid.uuid4()),
                task_id=task_id,
                topic="metric_analysis",
                statement=f"The {metric} metric is central to this analysis",
                rationale=f"User asked about {metric}",
                priority=80,
            )
            hypotheses.append(metric_hyp)

        # Add topic-based hypotheses
        for i, template in enumerate(templates):
            priority = 70 - (i * 10)  # Higher priority for first topics
            hypothesis = Hypothesis(
                hypothesis_id=str(uuid.uuid4()),
                task_id=task_id,
                topic=template["topic"],
                statement=template["statement"],
                rationale=template["rationale"],
                priority=priority,
            )
            hypotheses.append(hypothesis)

        # Add time-related hypotheses for comparison intents
        if intent_type in (IntentType.COMPARISON, IntentType.TREND_ANALYSIS):
            time_hyp = Hypothesis(
                hypothesis_id=str(uuid.uuid4()),
                task_id=task_id,
                topic="temporal_pattern",
                statement="The observed pattern follows a temporal trend",
                rationale="Time period analysis requested",
                priority=60,
            )
            hypotheses.append(time_hyp)

        # Add dimension-related hypotheses if dimensions specified
        if intent.dimensions:
            for dim in intent.dimensions[:2]:  # Limit to first 2 dimensions
                dim_hyp = Hypothesis(
                    hypothesis_id=str(uuid.uuid4()),
                    task_id=task_id,
                    topic=f"dimension_{dim}",
                    statement=f"Variation in {dim} explains the observed change",
                    rationale=f"Analysis by {dim} requested",
                    priority=65,
                )
                hypotheses.append(dim_hyp)

        # Store hypotheses
        for h in hypotheses:
            self._hypotheses[h.hypothesis_id] = h

        return hypotheses

    def update_with_observation(
        self,
        hypotheses: list[Hypothesis],
        observation: dict[str, Any],
    ) -> list[Hypothesis]:
        """Update hypothesis states based on new observation.

        Args:
            hypotheses: Current hypotheses
            observation: New observation from analysis

        Returns:
            Updated hypotheses
        """
        obs_type = observation.get("observation_type", "")
        obs_value = observation.get("numeric_values", {})

        for hypothesis in hypotheses:
            if hypothesis.is_resolved:
                continue

            hypothesis.state = HypothesisState.TESTING
            hypothesis.observations.append(observation.get("observation_id", ""))

            # Update confidence based on observation
            if obs_type == "metric_value":
                hypothesis.confidence = min(hypothesis.confidence + 0.2, 0.9)

            elif obs_type == "contribution_ranking":
                if hypothesis.topic in ("top_contributor", "quantity_driver", "price_driver"):
                    # Check if observation supports the hypothesis
                    if obs_value:
                        hypothesis.confidence = min(hypothesis.confidence + 0.3, 0.95)
                        hypothesis.state = HypothesisState.SUPPORTED

            elif obs_type == "trend" and hypothesis.topic == "trend_direction":
                direction = obs_value.get("direction", "")
                if "up" in direction.lower() or "down" in direction.lower():
                    hypothesis.confidence = min(hypothesis.confidence + 0.4, 0.95)
                    hypothesis.state = HypothesisState.SUPPORTED

            hypothesis.updated_at = datetime.now(UTC)

        return hypotheses

    def resolve_hypothesis(
        self,
        hypothesis: Hypothesis,
        state: HypothesisState,
        confidence: float,
        evidence_ids: list[str],
        limitations: list[str] | None = None,
    ) -> Hypothesis:
        """Manually resolve a hypothesis with evidence.

        Args:
            hypothesis: Hypothesis to resolve
            state: Final state
            confidence: Confidence level (0-1)
            evidence_ids: Supporting evidence IDs
            limitations: Any limitations on the conclusion

        Returns:
            Updated hypothesis
        """
        hypothesis.state = state
        hypothesis.confidence = confidence
        hypothesis.evidence_ids.extend(evidence_ids)
        if limitations:
            hypothesis.limitations.extend(limitations)
        hypothesis.updated_at = datetime.now(UTC)

        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        return hypothesis

    def rank_hypotheses(
        self,
        hypotheses: list[Hypothesis],
    ) -> list[Hypothesis]:
        """Rank hypotheses by priority and confidence.

        Args:
            hypotheses: Hypotheses to rank

        Returns:
            Sorted list (highest priority first)
        """
        return sorted(
            hypotheses,
            key=lambda h: (
                -h.priority,  # Higher priority first
                -h.confidence,  # Higher confidence first
                h.created_at,  # Older first if tied
            ),
        )

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        """Get a hypothesis by ID."""
        return self._hypotheses.get(hypothesis_id)

    def get_summary(self, hypotheses: list[Hypothesis]) -> dict[str, Any]:
        """Get a summary of hypothesis states.

        Returns:
            Summary dictionary
        """
        states = {}
        for h in hypotheses:
            state_key = h.state.value
            states[state_key] = states.get(state_key, 0) + 1

        return {
            "total": len(hypotheses),
            "resolved": len([h for h in hypotheses if h.is_resolved]),
            "unresolved": len([h for h in hypotheses if not h.is_resolved]),
            "by_state": states,
            "average_confidence": (
                sum(h.confidence for h in hypotheses) / len(hypotheses)
                if hypotheses
                else 0.0
            ),
        }
