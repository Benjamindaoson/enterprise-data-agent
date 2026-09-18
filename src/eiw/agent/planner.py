"""Analysis Planner - Creates structured analysis plans.

This module provides:
- Multi-step analysis planning
- Tool selection
- Dependency management
- Budget estimation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from eiw.agent.provider import ModelProvider, DeterministicProvider, ProviderConfig
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "planner")


# =============================================================================
# Tool Types
# =============================================================================


class ToolType(str, Enum):
    """Available analysis tools."""

    # Data access
    METRIC_QUERY = "metric_query"
    NL2SQL_QUERY = "nl2sql_query"
    METRIC_EXPLAIN = "metric_explain"

    # Analytical
    TREND_ANALYSIS = "trend_analysis"
    PERIOD_COMPARE = "period_compare"
    CONTRIBUTION_ANALYSIS = "contribution_analysis"
    PVM_ANALYSIS = "pvm_analysis"
    VARIANCE_ANALYSIS = "variance_analysis"
    DRILLDOWN_ANALYSIS = "drilldown_analysis"
    ANOMALY_ANALYSIS = "anomaly_analysis"

    # Knowledge
    KNOWLEDGE_SEARCH = "knowledge_search"

    # Computation
    PYTHON_ANALYSIS = "python_analysis"

    # Output
    CHART_GENERATE = "chart_generate"
    REPORT_GENERATE = "report_generate"


# =============================================================================
# Plan Step Model
# =============================================================================


class StepStatus(str, Enum):
    """Status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AnalysisStep:
    """A single step in an analysis plan."""

    step_id: str
    purpose: str
    tool: ToolType
    required_inputs: dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    verification_requirement: str = ""
    dependencies: list[str] = field(default_factory=list)
    budget_estimate_ms: int = 5000
    status: StepStatus = StepStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "purpose": self.purpose,
            "tool": self.tool.value,
            "required_inputs": self.required_inputs,
            "expected_output": self.expected_output,
            "verification_requirement": self.verification_requirement,
            "dependencies": self.dependencies,
            "budget_estimate_ms": self.budget_estimate_ms,
            "status": self.status.value,
        }


class AnalysisPlan(BaseModel):
    """Structured analysis plan."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(description="Unique plan identifier")
    intent_summary: str = Field(description="Summary of the resolved intent")

    steps: list[AnalysisStep] = Field(
        default_factory=list,
        description="Ordered list of analysis steps"
    )

    total_budget_ms: int = Field(
        default=60000,
        description="Total budget for all steps in milliseconds"
    )
    estimated_steps: int = Field(
        default=0,
        description="Estimated number of steps"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the plan was created"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional plan metadata"
    )

    def get_next_step(self) -> AnalysisStep | None:
        """Get the next pending step."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                deps_complete = all(
                    self._get_step(sid).status == StepStatus.COMPLETED
                    for sid in step.dependencies
                    if self._get_step(sid)
                )
                if deps_complete:
                    return step
        return None

    def get_step(self, step_id: str) -> AnalysisStep | None:
        """Get a step by ID."""
        return self._get_step(step_id)

    def _get_step(self, step_id: str) -> AnalysisStep | None:
        """Internal method to get step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def mark_step_complete(self, step_id: str) -> None:
        """Mark a step as complete."""
        step = self._get_step(step_id)
        if step:
            step.status = StepStatus.COMPLETED

    def mark_step_failed(self, step_id: str) -> None:
        """Mark a step as failed."""
        step = self._get_step(step_id)
        if step:
            step.status = StepStatus.FAILED

    def is_complete(self) -> bool:
        """Check if all steps are complete."""
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)
            for s in self.steps
        )

    def remaining_budget_ms(self, elapsed_ms: int = 0) -> int:
        """Calculate remaining budget."""
        return max(0, self.total_budget_ms - elapsed_ms)

    def to_trace_dict(self) -> dict[str, Any]:
        """Convert to dictionary for tracing."""
        return {
            "plan_id": self.plan_id,
            "step_count": len(self.steps),
            "total_budget_ms": self.total_budget_ms,
            "steps": [s.to_dict() for s in self.steps],
        }


# =============================================================================
# Planner
# =============================================================================


class AnalysisPlanner:
    """Creates structured analysis plans from resolved intent."""

    TOOL_SELECTION_RULES: dict[str, list[ToolType]] = {
        "descriptive": [ToolType.METRIC_QUERY, ToolType.PERIOD_COMPARE],
        "diagnostic": [
            ToolType.METRIC_QUERY,
            ToolType.CONTRIBUTION_ANALYSIS,
            ToolType.VARIANCE_ANALYSIS,
            ToolType.DRILLDOWN_ANALYSIS,
        ],
        "comparison": [ToolType.PERIOD_COMPARE, ToolType.CONTRIBUTION_ANALYSIS],
        "trend": [ToolType.TREND_ANALYSIS, ToolType.METRIC_QUERY],
        "contribution": [ToolType.CONTRIBUTION_ANALYSIS, ToolType.PVM_ANALYSIS],
        "variance": [ToolType.VARIANCE_ANALYSIS, ToolType.PERIOD_COMPARE],
        "anomaly": [ToolType.ANOMALY_ANALYSIS, ToolType.DRILLDOWN_ANALYSIS],
        "drilldown": [ToolType.DRILLDOWN_ANALYSIS, ToolType.METRIC_QUERY],
    }

    TOOL_BUDGETS: dict[ToolType, int] = {
        ToolType.METRIC_QUERY: 3000,
        ToolType.NL2SQL_QUERY: 10000,
        ToolType.METRIC_EXPLAIN: 2000,
        ToolType.TREND_ANALYSIS: 5000,
        ToolType.PERIOD_COMPARE: 5000,
        ToolType.CONTRIBUTION_ANALYSIS: 8000,
        ToolType.PVM_ANALYSIS: 8000,
        ToolType.VARIANCE_ANALYSIS: 6000,
        ToolType.DRILLDOWN_ANALYSIS: 5000,
        ToolType.ANOMALY_ANALYSIS: 6000,
        ToolType.KNOWLEDGE_SEARCH: 3000,
        ToolType.PYTHON_ANALYSIS: 15000,
        ToolType.CHART_GENERATE: 3000,
        ToolType.REPORT_GENERATE: 5000,
    }

    def __init__(
        self,
        provider: ModelProvider | None = None,
        max_budget_ms: int = 60000,
    ):
        """Initialize planner."""
        self._provider = provider or DeterministicProvider(ProviderConfig())
        self._max_budget_ms = max_budget_ms
        self._plan_count = 0

    @property
    def plan_count(self) -> int:
        """Number of plans created."""
        return self._plan_count

    async def create_plan(
        self,
        intent: Any,
        question: str = "",
        domain: str = "general",
    ) -> AnalysisPlan:
        """Create an analysis plan from resolved intent."""
        with trace_span("plan.create", {
            "analysis_type": intent.analysis_type.value if hasattr(intent, 'analysis_type') else "unknown",
            "domain": domain,
        }):
            self._plan_count += 1
            plan_id = f"plan_{self._plan_count}_{int(datetime.now().timestamp())}"

            if self._should_use_model_planning(intent):
                plan = await self._create_model_plan(plan_id, intent, question, domain)
            else:
                plan = self._create_rule_based_plan(plan_id, intent, question, domain)

            if not self._validate_plan(plan):
                logger.warning(f"Plan validation failed for {plan_id}")

            return plan

    def _should_use_model_planning(self, intent: Any) -> bool:
        """Determine if model-based planning is needed."""
        analysis_type = intent.analysis_type
        # Handle both enum and string comparisons
        if hasattr(analysis_type, 'value'):
            analysis_type = analysis_type.value
        if analysis_type in ("diagnostic", "drilldown"):
            return True
        if len(intent.metric_candidates) > 2:
            return True
        return False

    async def _create_model_plan(
        self,
        plan_id: str,
        intent: Any,
        question: str,
        domain: str,
    ) -> AnalysisPlan:
        """Create plan using model."""
        prompt = self._build_planning_prompt(intent, question, domain)

        response = await self._provider.complete(prompt)
        if response.error:
            return self._create_rule_based_plan(plan_id, intent, question, domain)

        return self._parse_model_plan(plan_id, response.content, intent)

    def _create_rule_based_plan(
        self,
        plan_id: str,
        intent: Any,
        question: str,
        domain: str,
    ) -> AnalysisPlan:
        """Create plan using rules."""
        steps: list[AnalysisStep] = []
        step_num = 0

        # Normalize analysis_type for comparisons
        analysis_type = intent.analysis_type
        if hasattr(analysis_type, 'value'):
            analysis_type = analysis_type.value

        primary_metric = intent.selected_metrics[0] if intent.selected_metrics else intent.metric_candidates[0] if intent.metric_candidates else "unknown"

        step_num += 1
        steps.append(AnalysisStep(
            step_id=f"{plan_id}_step_{step_num}",
            purpose=f"Retrieve {primary_metric} data",
            tool=ToolType.METRIC_QUERY,
            required_inputs={
                "metrics": [primary_metric],
                "dimensions": intent.selected_dimensions,
            },
            expected_output="Metric data with specified dimensions",
            verification_requirement="Data retrieved successfully",
            budget_estimate_ms=self.TOOL_BUDGETS[ToolType.METRIC_QUERY],
        ))

        if analysis_type in ("comparison", "diagnostic"):
            if intent.comparison_baseline:
                step_num += 1
                steps.append(AnalysisStep(
                    step_id=f"{plan_id}_step_{step_num}",
                    purpose="Compare with baseline period",
                    tool=ToolType.PERIOD_COMPARE,
                    expected_output="Period comparison with variance",
                    verification_requirement="Comparison computed",
                    dependencies=[f"{plan_id}_step_1"],
                    budget_estimate_ms=self.TOOL_BUDGETS[ToolType.PERIOD_COMPARE],
                ))

            if analysis_type == "diagnostic" and intent.selected_dimensions:
                step_num += 1
                steps.append(AnalysisStep(
                    step_id=f"{plan_id}_step_{step_num}",
                    purpose="Identify key drivers",
                    tool=ToolType.CONTRIBUTION_ANALYSIS,
                    required_inputs={"breakdown_by": intent.selected_dimensions[0]},
                    expected_output="Contribution breakdown by dimension",
                    verification_requirement="Contributions sum to 100%",
                    dependencies=[f"{plan_id}_step_1"],
                    budget_estimate_ms=self.TOOL_BUDGETS[ToolType.CONTRIBUTION_ANALYSIS],
                ))

        elif analysis_type == "trend":
            step_num += 1
            steps.append(AnalysisStep(
                step_id=f"{plan_id}_step_{step_num}",
                purpose="Analyze trend",
                tool=ToolType.TREND_ANALYSIS,
                required_inputs={"granularity": intent.time_granularity or "monthly"},
                expected_output="Trend analysis with direction and magnitude",
                verification_requirement="Trend direction identified",
                dependencies=[f"{plan_id}_step_1"],
                budget_estimate_ms=self.TOOL_BUDGETS[ToolType.TREND_ANALYSIS],
            ))

        elif analysis_type == "variance":
            step_num += 1
            steps.append(AnalysisStep(
                step_id=f"{plan_id}_step_{step_num}",
                purpose="Analyze variance",
                tool=ToolType.VARIANCE_ANALYSIS,
                required_inputs={"baseline": "budget"},
                expected_output="Variance breakdown",
                verification_requirement="Variance reconciled",
                dependencies=[f"{plan_id}_step_1"],
                budget_estimate_ms=self.TOOL_BUDGETS[ToolType.VARIANCE_ANALYSIS],
            ))

        step_num += 1
        output_tool = ToolType.CHART_GENERATE if hasattr(intent, 'requested_output') and intent.requested_output.value == "chart" else ToolType.REPORT_GENERATE

        steps.append(AnalysisStep(
            step_id=f"{plan_id}_step_{step_num}",
            purpose="Generate output",
            tool=output_tool,
            expected_output="Output generated successfully",
            dependencies=[f"{plan_id}_step_{step_num - 1}"] if step_num > 1 else [],
            budget_estimate_ms=self.TOOL_BUDGETS[output_tool],
        ))

        total_budget = sum(s.budget_estimate_ms for s in steps)

        return AnalysisPlan(
            plan_id=plan_id,
            intent_summary=intent.objective if hasattr(intent, 'objective') else question,
            steps=steps,
            total_budget_ms=min(total_budget, self._max_budget_ms),
            estimated_steps=len(steps),
            metadata={
                "analysis_type": intent.analysis_type.value if hasattr(intent, 'analysis_type') else "unknown",
                "domain": domain,
                "planning_method": "rule_based",
            },
        )

    def _build_planning_prompt(
        self,
        intent: Any,
        question: str,
        domain: str,
    ) -> str:
        """Build prompt for model-based planning."""
        return f"""Create an analysis plan for this business question.

Intent:
- Objective: {intent.objective if hasattr(intent, 'objective') else question}
- Analysis type: {intent.analysis_type.value if hasattr(intent, 'analysis_type') else 'unknown'}
- Metrics: {intent.selected_metrics or intent.metric_candidates}
- Dimensions: {intent.selected_dimensions or intent.dimension_candidates}
- Time range: {intent.time_range_start} to {intent.time_range_end}
- Output: {intent.requested_output.value if hasattr(intent, 'requested_output') else 'text'}

Available tools: metric_query, period_compare, trend_analysis, contribution_analysis, pvm_analysis, variance_analysis, drilldown_analysis, anomaly_analysis, python_analysis, chart_generate, report_generate

Create 3-5 steps. Each step needs:
- step_id (e.g., plan_1_step_1)
- purpose (what this step accomplishes)
- tool (which tool to use)
- required_inputs (what inputs are needed)
- expected_output (what this step produces)
- dependencies (which step_ids must complete first)
- budget_estimate_ms (time budget for this step)

Respond with JSON array of steps."""

    def _parse_model_plan(
        self,
        plan_id: str,
        content: str,
        intent: Any,
    ) -> AnalysisPlan:
        """Parse model response into plan."""
        import json

        steps: list[AnalysisStep] = []

        try:
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            for step_data in data if isinstance(data, list) else data.get("steps", []):
                steps.append(AnalysisStep(
                    step_id=step_data.get("step_id", f"{plan_id}_step_{len(steps) + 1}"),
                    purpose=step_data.get("purpose", ""),
                    tool=ToolType(step_data.get("tool", "metric_query")),
                    required_inputs=step_data.get("required_inputs", {}),
                    expected_output=step_data.get("expected_output", ""),
                    dependencies=step_data.get("dependencies", []),
                    budget_estimate_ms=step_data.get("budget_estimate_ms", 5000),
                ))

        except Exception as e:
            logger.warning(f"Failed to parse model plan: {e}, using rule-based")
            return self._create_rule_based_plan(plan_id, intent, "", "general")

        total_budget = sum(s.budget_estimate_ms for s in steps) if steps else 0

        return AnalysisPlan(
            plan_id=plan_id,
            intent_summary=intent.objective if hasattr(intent, 'objective') else "",
            steps=steps,
            total_budget_ms=min(total_budget, self._max_budget_ms),
            estimated_steps=len(steps),
            metadata={
                "analysis_type": intent.analysis_type.value if hasattr(intent, 'analysis_type') else "unknown",
                "domain": intent.domain if hasattr(intent, 'domain') else "general",
                "planning_method": "model_based",
            },
        )

    def _extract_json(self, content: str) -> str:
        """Extract JSON from content."""
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    def _validate_plan(self, plan: AnalysisPlan) -> bool:
        """Validate plan feasibility."""
        if not plan.steps:
            return False

        total_budget = sum(s.budget_estimate_ms for s in plan.steps)
        if total_budget > self._max_budget_ms:
            return False

        all_step_ids = {s.step_id for s in plan.steps}
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in all_step_ids:
                    logger.warning(f"Invalid dependency: {dep} in step {step.step_id}")
                    return False

        return True


def create_analysis_planner(
    provider: ModelProvider | None = None,
    max_budget_ms: int = 60000,
) -> AnalysisPlanner:
    """Create an analysis planner."""
    return AnalysisPlanner(provider=provider, max_budget_ms=max_budget_ms)
