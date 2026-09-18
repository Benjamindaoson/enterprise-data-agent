"""Analysis Planner for Enterprise Data Agent.

Creates structured analysis plans based on:
- Resolved business intent
- Available metrics/dimensions
- User permissions
- Budget constraints
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from eiw.agent.intent_resolver import IntentResult, IntentType


@dataclass
class PlanStep:
    """A single step in an analysis plan."""

    step_id: str
    ordinal: int
    title: str
    purpose: str
    tool: str
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_outputs: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    estimated_duration_seconds: int = 30


@dataclass
class AnalysisPlan:
    """A structured analysis plan."""

    plan_id: str
    task_id: str
    intent_type: str
    steps: list[PlanStep] = field(default_factory=list)
    max_steps: int = 10
    max_duration_seconds: int = 300
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "intent_type": self.intent_type,
            "steps": [
                {
                    "step_id": s.step_id,
                    "ordinal": s.ordinal,
                    "title": s.title,
                    "purpose": s.purpose,
                    "tool": s.tool,
                    "inputs": s.inputs,
                    "expected_outputs": s.expected_outputs,
                    "stop_conditions": s.stop_conditions,
                    "depends_on": s.depends_on,
                    "estimated_duration_seconds": s.estimated_duration_seconds,
                }
                for s in self.steps
            ],
            "max_steps": self.max_steps,
            "max_duration_seconds": self.max_duration_seconds,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }


class AnalysisPlanner:
    """Creates analysis plans for business questions.

    The planner takes a resolved intent and creates a structured
    sequence of analytical steps to answer the question.
    """

    # Step templates for different intents
    INTENT_STEPS: dict[IntentType, list[dict[str, str]]] = {
        IntentType.METRIC_QUERY: [
            {"title": "Establish baseline", "purpose": "metric_query", "tool": "metric_query"},
            {"title": "Present findings", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.TREND_ANALYSIS: [
            {"title": "Calculate trend", "purpose": "trend_analysis", "tool": "trend_analysis"},
            {"title": "Present findings", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.COMPARISON: [
            {"title": "Calculate current period", "purpose": "metric_query", "tool": "metric_query"},
            {"title": "Calculate comparison period", "purpose": "metric_query", "tool": "metric_query"},
            {"title": "Compare periods", "purpose": "period_compare", "tool": "period_compare"},
            {"title": "Present findings", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.CONTRIBUTION: [
            {"title": "Calculate total change", "purpose": "metric_query", "tool": "metric_query"},
            {"title": "Rank contributors", "purpose": "contribution", "tool": "contribution_analysis"},
            {"title": "Verify contributions", "purpose": "verify", "tool": "nl2sql_explain"},
            {"title": "Present findings", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.ATTRIBUTION: [
            {"title": "Establish baseline", "purpose": "metric_query", "tool": "metric_query"},
            {"title": "Rank contributions", "purpose": "contribution", "tool": "contribution_analysis"},
            {"title": "Investigate top drivers", "purpose": "investigation", "tool": "nl2sql_query"},
            {"title": "Verify causality", "purpose": "verify", "tool": "nl2sql_explain"},
            {"title": "Synthesize findings", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.ANOMALY_DETECTION: [
            {"title": "Establish baseline", "purpose": "trend_analysis", "tool": "trend_analysis"},
            {"title": "Detect anomalies", "purpose": "anomaly", "tool": "anomaly_detection"},
            {"title": "Investigate anomaly", "purpose": "investigation", "tool": "nl2sql_query"},
            {"title": "Present findings", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.EXPLAIN: [
            {"title": "Retrieve definition", "purpose": "explain", "tool": "metric_explain"},
            {"title": "Provide explanation", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.BUDGET_VARIANCE: [
            {"title": "Calculate actuals", "purpose": "metric_query", "tool": "metric_query"},
            {"title": "Compare to budget", "purpose": "variance", "tool": "variance_analysis"},
            {"title": "Investigate variances", "purpose": "investigation", "tool": "nl2sql_query"},
            {"title": "Present findings", "purpose": "report", "tool": "report_generate"},
        ],
        IntentType.drilldown: [
            {"title": "Establish baseline", "purpose": "metric_query", "tool": "metric_query"},
            {"title": "Drill down by dimension", "purpose": "drilldown", "tool": "drilldown_analysis"},
            {"title": "Continue drilldown", "purpose": "drilldown", "tool": "drilldown_analysis"},
            {"title": "Present findings", "purpose": "report", "tool": "report_generate"},
        ],
    }

    def create_plan(
        self,
        task_id: str,
        intent: IntentResult,
        user_context: dict[str, Any] | None = None,
    ) -> AnalysisPlan:
        """Create an analysis plan for the given intent.

        Args:
            task_id: Task identifier
            intent: Resolved business intent
            user_context: User context for budget limits

        Returns:
            AnalysisPlan with ordered steps
        """
        plan_id = str(uuid.uuid4())
        intent_type = intent.intent_type

        # Get step templates for this intent type
        templates = self.INTENT_STEPS.get(
            intent_type,
            self.INTENT_STEPS(IntentType.METRIC_QUERY),
        )

        # Create steps
        steps: list[PlanStep] = []
        for i, template in enumerate(templates, 1):
            step = PlanStep(
                step_id=str(uuid.uuid4()),
                ordinal=i,
                title=template["title"],
                purpose=template["purpose"],
                tool=template["tool"],
                inputs=self._prepare_step_inputs(intent, template),
                expected_outputs=self._get_expected_outputs(template["purpose"]),
                stop_conditions=self._get_stop_conditions(template["purpose"]),
                estimated_duration_seconds=self._estimate_duration(template["tool"]),
            )
            steps.append(step)

        # Create plan
        plan = AnalysisPlan(
            plan_id=plan_id,
            task_id=task_id,
            intent_type=intent_type.value,
            steps=steps,
            max_steps=len(steps),
            max_duration_seconds=sum(s.estimated_duration_seconds for s in steps) + 60,
        )

        return plan

    def _prepare_step_inputs(
        self,
        intent: IntentResult,
        template: dict[str, str],
    ) -> dict[str, Any]:
        """Prepare inputs for a step based on template."""
        inputs: dict[str, Any] = {}

        if template["purpose"] in ("metric_query", "trend_analysis", "period_compare"):
            inputs["metric_ids"] = intent.primary_metrics
            inputs["dimensions"] = intent.dimensions
            inputs["filters"] = intent.filters
            if intent.primary_period_start and intent.primary_period_end:
                inputs["period"] = {
                    "start": intent.primary_period_start.isoformat(),
                    "end": intent.primary_period_end.isoformat(),
                }
            if intent.comparison_period_start and intent.comparison_period_end:
                inputs["comparison_period"] = {
                    "start": intent.comparison_period_start.isoformat(),
                    "end": intent.comparison_period_end.isoformat(),
                }

        elif template["purpose"] == "contribution":
            inputs["metric_id"] = intent.primary_metrics[0] if intent.primary_metrics else "revenue"
            inputs["dimension"] = intent.dimensions[0] if intent.dimensions else "category"
            inputs["granularity"] = intent.granularity

        elif template["purpose"] == "investigation":
            inputs["question"] = intent.raw_components.get("question", "")
            inputs["metrics"] = intent.primary_metrics

        return inputs

    def _get_expected_outputs(self, purpose: str) -> list[str]:
        """Get expected outputs for a step purpose."""
        output_map: dict[str, list[str]] = {
            "metric_query": ["metric_values", "row_count", "execution_time_ms"],
            "trend_analysis": ["data_points", "trend_direction", "growth_rate"],
            "period_compare": ["changes", "change_pct", "direction"],
            "contribution": ["ranked_contributors", "total_change", "contribution_pct"],
            "investigation": ["sql_query", "results", "explanation"],
            "anomaly": ["anomalies", "threshold", "severity"],
            "variance": ["variance", "variance_pct", "favorable"],
            "drilldown": ["level_data", "next_dimensions"],
            "verify": ["verified", "confidence", "evidence"],
            "report": ["report_uri", "claims", "summary"],
            "explain": ["definition", "formula", "examples"],
        }
        return output_map.get(purpose, ["result"])

    def _get_stop_conditions(self, purpose: str) -> list[str]:
        """Get stop conditions for a step purpose."""
        stop_map: dict[str, list[str]] = {
            "metric_query": ["no_data_returned", "timeout_exceeded"],
            "contribution": ["no_significant_contributors", "too_many_dimensions"],
            "investigation": ["no_clear_findings", "max_retries_exceeded"],
            "anomaly": ["no_anomalies_found", "all_anomalies_explained"],
            "drilldown": ["max_depth_reached", "no_variance_at_level"],
        }
        return stop_map.get(purpose, [])

    def _estimate_duration(self, tool: str) -> int:
        """Estimate step duration in seconds."""
        duration_map: dict[str, int] = {
            "metric_query": 5,
            "trend_analysis": 10,
            "period_compare": 8,
            "contribution_analysis": 15,
            "nl2sql_query": 30,
            "nl2sql_explain": 10,
            "anomaly_detection": 20,
            "variance_analysis": 15,
            "drilldown_analysis": 20,
            "metric_explain": 5,
            "report_generate": 10,
            "python_analysis": 30,
        }
        return duration_map.get(tool, 15)

    def extend_plan(
        self,
        plan: AnalysisPlan,
        additional_steps: list[dict[str, str]],
    ) -> AnalysisPlan:
        """Extend an existing plan with additional steps.

        Args:
            plan: Existing plan to extend
            additional_steps: List of step templates to add

        Returns:
            Extended plan with new steps
        """
        base_ordinal = len(plan.steps)

        for i, template in enumerate(additional_steps, 1):
            step = PlanStep(
                step_id=str(uuid.uuid4()),
                ordinal=base_ordinal + i,
                title=template["title"],
                purpose=template["purpose"],
                tool=template["tool"],
                inputs={},
                expected_outputs=self._get_expected_outputs(template["purpose"]),
                stop_conditions=self._get_stop_conditions(template["purpose"]),
                estimated_duration_seconds=self._estimate_duration(template["tool"]),
            )
            plan.steps.append(step)

        plan.max_steps = len(plan.steps)
        plan.version += 1
        return plan

    def validate_plan(self, plan: AnalysisPlan) -> tuple[bool, list[str]]:
        """Validate a plan for correctness.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: list[str] = []

        # Check step ordinals are sequential
        ordinals = [s.ordinal for s in plan.steps]
        if ordinals != list(range(1, len(ordinals) + 1)):
            errors.append("Step ordinals must be sequential starting from 1")

        # Check dependencies are valid
        all_step_ids = {s.step_id for s in plan.steps}
        for step in plan.steps:
            for dep_id in step.depends_on:
                if dep_id not in all_step_ids:
                    errors.append(f"Step {step.step_id} depends on unknown step {dep_id}")

        # Check tool is specified
        for step in plan.steps:
            if not step.tool:
                errors.append(f"Step {step.step_id} has no tool specified")

        return len(errors) == 0, errors
