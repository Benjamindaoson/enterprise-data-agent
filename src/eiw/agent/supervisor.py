"""Supervisor Runtime - Multi-step investigation loop.

This module provides:
- Supervisor decision loop
- Tool execution
- Observation recording
- Hypothesis management
- Budget tracking
- Checkpoint/resume
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field, ConfigDict

from eiw.agent.provider import ModelProvider, DeterministicProvider, ProviderConfig
from eiw.agent.planner import AnalysisPlan, AnalysisStep, StepStatus, ToolType
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "supervisor")


# =============================================================================
# Supervisor Decision Types
# =============================================================================


class SupervisorDecision(str, Enum):
    """Decisions the supervisor can make."""

    EXECUTE_STEP = "execute_step"  # Execute next step
    REFINED_PLAN = "refine_plan"  # Modify the plan
    DRILL_DOWN = "drill_down"  # Dive deeper into an observation
    REQUEST_CLARIFICATION = "request_clarification"  # Ask user
    RETRY = "retry"  # Retry failed step
    SYNTHESIZE = "synthesize"  # Synthesize from observations
    COMPLETE_PARTIAL = "complete_partial"  # Complete with limitations
    STOP_FAILED = "stop_failed"  # Stop due to failures
    STOP_SUCCESS = "stop_success"  # All done


# =============================================================================
# Hypothesis Management
# =============================================================================


class HypothesisStatus(str, Enum):
    """Hypothesis status."""

    PROPOSED = "proposed"  # Initial hypothesis
    TESTING = "testing"  # Being tested
    SUPPORTED = "supported"  # Evidence supports
    WEAKENED = "weakened"  # Evidence weakens
    REFUTED = "refuted"  # Evidence contradicts
    UNRESOLVED = "unresolved"  # Cannot determine


class ConfidenceCategory(str, Enum):
    """Confidence categories (not just model-reported numbers)."""

    HIGH = "high"  # Strong evidence
    MEDIUM = "medium"  # Some evidence
    LOW = "low"  # Weak evidence
    NONE = "none"  # No evidence


@dataclass
class Hypothesis:
    """A hypothesis to test during analysis."""

    hypothesis_id: str
    statement: str
    hypothesis_type: str  # "causal", "correlation", "descriptive"
    evidence_for: list[str] = field(default_factory=list)  # Observation IDs
    evidence_against: list[str] = field(default_factory=list)  # Observation IDs
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence_category: ConfidenceCategory = ConfidenceCategory.NONE
    next_test: str = ""  # What would test this hypothesis
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "statement": self.statement,
            "type": self.hypothesis_type,
            "status": self.status.value,
            "confidence_category": self.confidence_category.value,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "next_test": self.next_test,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def support(self, observation_id: str) -> None:
        """Add supporting evidence."""
        if observation_id not in self.evidence_for:
            self.evidence_for.append(observation_id)
            self._update_confidence()
            self.updated_at = datetime.now()

    def weaken(self, observation_id: str) -> None:
        """Add weakening evidence."""
        if observation_id not in self.evidence_against:
            self.evidence_against.append(observation_id)
            self._update_confidence()
            self.updated_at = datetime.now()

    def _update_confidence(self) -> None:
        """Update confidence based on evidence."""
        for_count = len(self.evidence_for)
        against_count = len(self.evidence_against)
        total = for_count + against_count

        if total == 0:
            self.confidence_category = ConfidenceCategory.NONE
        elif for_count == 0:
            self.confidence_category = ConfidenceCategory.NONE
            self.status = HypothesisStatus.REFUTED
        elif against_count == 0:
            if for_count >= 3:
                self.confidence_category = ConfidenceCategory.HIGH
                self.status = HypothesisStatus.SUPPORTED
            elif for_count >= 2:
                self.confidence_category = ConfidenceCategory.MEDIUM
            else:
                self.confidence_category = ConfidenceCategory.LOW
        else:
            if for_count > against_count * 2:
                self.confidence_category = ConfidenceCategory.MEDIUM
                self.status = HypothesisStatus.SUPPORTED
            elif against_count > for_count:
                self.confidence_category = ConfidenceCategory.LOW
                self.status = HypothesisStatus.WEAKENED
            else:
                self.confidence_category = ConfidenceCategory.NONE
                self.status = HypothesisStatus.UNRESOLVED


# =============================================================================
# Observation and Evidence
# =============================================================================


@dataclass
class ToolExecution:
    """Record of a tool execution."""

    execution_id: str
    tool_name: str
    tool_inputs: dict[str, Any]
    outputs: Any
    start_time: datetime
    end_time: datetime | None = None
    error: str | None = None
    status: str = "pending"  # pending, running, success, failed
    observation_id: str | None = None

    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0


@dataclass
class Observation:
    """An observation from tool execution."""

    observation_id: str
    tool_execution_id: str
    content: str
    data: Any  # Structured data from tool
    timestamp: datetime = field(default_factory=datetime.now)
    hypotheses_affected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "tool_execution_id": self.tool_execution_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "hypotheses_affected": self.hypotheses_affected,
        }


@dataclass
class Claim:
    """A claim derived from observations."""

    claim_id: str
    statement: str
    evidence_ids: list[str]  # Observation IDs
    confidence: float  # 0-1
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Runtime State
# =============================================================================


class TaskStatus(str, Enum):
    """Status of an analysis task."""

    CREATED = "created"
    RUNNING = "running"
    WAITING_CLARIFICATION = "waiting_clarification"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisTask(BaseModel):
    """Analysis task state."""

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(description="Unique task identifier")
    question: str = Field(description="Original question")

    # Status
    status: TaskStatus = Field(default=TaskStatus.CREATED)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Intent and Plan
    intent: dict[str, Any] | None = Field(default=None)
    plan: dict[str, Any] | None = Field(default=None)

    # State
    current_step_id: str | None = Field(default=None)
    completed_steps: list[str] = Field(default_factory=list)
    failed_steps: list[str] = Field(default_factory=list)

    # Data
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    tool_executions: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)

    # Budget
    total_budget_ms: int = Field(default=60000)
    elapsed_ms: int = Field(default=0)
    retry_count: int = Field(default=0)

    # Metadata
    domain: str = Field(default="")
    error: str | None = Field(default=None)


# =============================================================================
# Supervisor
# =============================================================================


class Supervisor:
    """Supervisor for multi-step investigation loop.

    The supervisor:
    1. Manages task state
    2. Decides next action based on observations
    3. Executes tools
    4. Records observations
    5. Updates hypotheses
    6. Tracks budget
    7. Handles checkpoint/resume
    """

    def __init__(
        self,
        provider: ModelProvider | None = None,
        max_retries: int = 3,
        max_budget_ms: int = 60000,
    ):
        """Initialize supervisor.

        Args:
            provider: Model provider
            max_retries: Maximum retry attempts
            max_budget_ms: Maximum total budget
        """
        self._provider = provider or DeterministicProvider(ProviderConfig())
        self._max_retries = max_retries
        self._max_budget_ms = max_budget_ms
        self._task: AnalysisTask | None = None
        self._tool_registry: dict[ToolType, Callable] = {}
        self._execution_count = 0
        self._start_time: datetime | None = None

    def register_tool(self, tool_type: ToolType, handler: Callable) -> None:
        """Register a tool handler.

        Args:
            tool_type: Type of tool
            handler: Async function to execute tool
        """
        self._tool_registry[tool_type] = handler

    async def run(
        self,
        task: AnalysisTask,
        intent: Any,
        plan: AnalysisPlan,
    ) -> AnalysisTask:
        """Run the supervisor loop.

        Args:
            task: Analysis task
            intent: Resolved intent
            plan: Analysis plan

        Returns:
            Updated task with results
        """
        self._task = task
        self._task.status = TaskStatus.RUNNING
        self._task.started_at = datetime.now()
        self._task.plan = plan.to_trace_dict()
        self._start_time = datetime.now()

        logger.info(f"Supervisor starting task {task.task_id}")

        with trace_span("agent.supervisor.run", {
            "task_id": task.task_id,
            "plan_steps": len(plan.steps),
            "total_budget_ms": plan.total_budget_ms,
        }):
            while not plan.is_complete() and self._has_budget():
                # Get next step
                next_step = plan.get_next_step()
                if not next_step:
                    break

                # Make decision
                decision = await self._decide(
                    plan=plan,
                    step=next_step,
                )

                logger.info(
                    f"Supervisor decision: {decision.decision.value}",
                    extra={"step_id": next_step.step_id, "reason": decision.reason}
                )

                # Execute decision
                if decision.decision == SupervisorDecision.EXECUTE_STEP:
                    result = await self._execute_step(plan, next_step)
                    if not result.success:
                        # Check if should retry
                        if self._task.retry_count < self._max_retries:
                            decision = SupervisorDecision.RETRY
                        else:
                            decision = SupervisorDecision.STOP_FAILED

                elif decision.decision == SupervisorDecision.SYNTHESIZE:
                    await self._synthesize_claims()
                    break

                elif decision.decision in (SupervisorDecision.STOP_FAILED, SupervisorDecision.COMPLETE_PARTIAL):
                    self._task.status = TaskStatus.PARTIAL if decision == SupervisorDecision.COMPLETE_PARTIAL else TaskStatus.FAILED
                    break

                # Update budget
                self._task.elapsed_ms = int((datetime.now() - self._start_time).total_seconds() * 1000)

            # Check final status
            if plan.is_complete():
                self._task.status = TaskStatus.COMPLETED

            self._task.completed_at = datetime.now()

            logger.info(
                f"Supervisor completed task {task.task_id}",
                extra={"status": self._task.status.value, "elapsed_ms": self._task.elapsed_ms}
            )

            return self._task

    async def _decide(
        self,
        plan: AnalysisPlan,
        step: AnalysisStep,
    ) -> tuple[SupervisorDecision, str]:
        """Decide next action.

        Args:
            plan: Current plan
            step: Next step to execute

        Returns:
            Tuple of (decision, reason)
        """
        # Use provider for complex decisions
        if len(self._task.observations) >= 2 and step.purpose:
            prompt = f"""Based on these observations:
{self._format_observations()}

Current step: {step.purpose}
Tool: {step.tool.value}

Decide: execute_step, synthesize, drill_down, refine_plan, or stop_failed.

Respond with JSON: {{"decision": "...", "reason": "..."}}"""

            response = await self._provider.complete(prompt)
            if not response.error:
                try:
                    import json
                    data = json.loads(self._extract_json(response.content))
                    decision = SupervisorDecision(data.get("decision", "execute_step"))
                    return decision, data.get("reason", "")
                except Exception:
                    pass

        # Default: execute step
        return SupervisorDecision.EXECUTE_STEP, "Proceeding with next step"

    async def _execute_step(
        self,
        plan: AnalysisPlan,
        step: AnalysisStep,
    ) -> tuple[bool, str]:
        """Execute a plan step.

        Args:
            plan: Analysis plan
            step: Step to execute

        Returns:
            Tuple of (success, error_message)
        """
        tool_type = step.tool
        handler = self._tool_registry.get(tool_type)

        if not handler:
            logger.warning(f"No handler for tool {tool_type}")
            plan.mark_step_failed(step.step_id)
            return False, f"No handler for tool {tool_type}"

        # Record execution
        execution = ToolExecution(
            execution_id=f"exec_{self._execution_count}",
            tool_name=tool_type.value,
            tool_inputs=step.required_inputs,
            outputs=None,
            start_time=datetime.now(),
            status="running",
        )
        self._execution_count += 1

        try:
            # Execute tool
            result = await handler(**step.required_inputs)

            # Record success
            execution.outputs = result
            execution.end_time = datetime.now()
            execution.status = "success"

            # Create observation
            observation = Observation(
                observation_id=f"obs_{len(self._task.observations)}",
                tool_execution_id=execution.execution_id,
                content=str(result)[:500],  # Truncate for storage
                data=result,
            )

            # Update task
            self._task.observations.append(observation.to_dict())
            self._task.tool_executions.append({
                "execution_id": execution.execution_id,
                "tool_name": execution.tool_name,
                "status": execution.status,
                "duration_ms": execution.duration_ms(),
            })

            # Update plan
            plan.mark_step_complete(step.step_id)
            self._task.completed_steps.append(step.step_id)

            # Check if this observation affects any hypotheses
            await self._update_hypotheses(observation)

            return True, ""

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            execution.end_time = datetime.now()
            execution.status = "failed"
            execution.error = str(e)

            self._task.tool_executions.append({
                "execution_id": execution.execution_id,
                "tool_name": execution.tool_name,
                "status": "failed",
                "error": str(e),
            })

            plan.mark_step_failed(step.step_id)
            self._task.failed_steps.append(step.step_id)
            self._task.retry_count += 1

            return False, str(e)

    async def _update_hypotheses(self, observation: Observation) -> None:
        """Update hypotheses based on observation.

        Args:
            observation: New observation
        """
        for hyp_dict in self._task.hypotheses:
            # Check if this observation is relevant
            # For now, add to evidence_for for all active hypotheses
            if hyp_dict.get("status") in ("proposed", "testing"):
                if observation.observation_id not in hyp_dict.get("evidence_for", []):
                    hyp_dict.setdefault("evidence_for", []).append(observation.observation_id)

    async def _synthesize_claims(self) -> None:
        """Synthesize claims from observations."""
        if not self._task.observations:
            return

        claim_id = f"claim_{len(self._task.claims)}"
        claim = Claim(
            claim_id=claim_id,
            statement=f"Analysis completed with {len(self._task.observations)} observations",
            evidence_ids=[o["observation_id"] for o in self._task.observations[-3:]],
            confidence=0.8,
        )

        self._task.claims.append(claim.to_dict())

    def _format_observations(self) -> str:
        """Format observations for prompt."""
        lines = []
        for obs in self._task.observations[-5:]:
            lines.append(f"- {obs.get('content', '')[:200]}")
        return "\n".join(lines) if lines else "No observations yet"

    def _has_budget(self) -> bool:
        """Check if budget remains."""
        elapsed = int((datetime.now() - self._start_time).total_seconds() * 1000) if self._start_time else 0
        return elapsed < self._max_budget_ms

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

    def get_task(self) -> AnalysisTask | None:
        """Get current task."""
        return self._task

    def get_state(self) -> dict[str, Any]:
        """Get serializable state for checkpoint."""
        if not self._task:
            return {}

        return {
            "task": self._task.model_dump(),
            "execution_count": self._execution_count,
            "timestamp": datetime.now().isoformat(),
        }

    def load_state(self, state: dict[str, Any]) -> None:
        """Load state from checkpoint.

        Args:
            state: Saved state
        """
        task_data = state.get("task", {})
        self._task = AnalysisTask(**task_data)
        self._execution_count = state.get("execution_count", 0)


def create_supervisor(
    provider: ModelProvider | None = None,
    max_retries: int = 3,
    max_budget_ms: int = 60000,
) -> Supervisor:
    """Create a supervisor.

    Args:
        provider: Model provider
        max_retries: Maximum retries
        max_budget_ms: Maximum budget

    Returns:
        Supervisor instance
    """
    return Supervisor(
        provider=provider,
        max_retries=max_retries,
        max_budget_ms=max_budget_ms,
    )
