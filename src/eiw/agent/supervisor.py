"""Supervisor Agent for Enterprise Data Agent.

The Supervisor Agent coordinates the entire analysis workflow:
- Intent Resolution
- Semantic Resolution
- Planning
- Tool Orchestration
- Hypothesis Management
- Verification
- Report Synthesis

This implements the Supervisor-Executor architecture where:
- Supervisor owns decomposition, routing, replanning, and stop decisions
- Specialized executors work inside bounded responsibilities
- Agents exchange structured observations through shared state
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from eiw.agent.hypothesis import Hypothesis, HypothesisManager
from eiw.agent.intent_resolver import IntentResolver, IntentResult
from eiw.agent.planner import AnalysisPlan, AnalysisPlanner
from eiw.agent.router import RoutingDecision, ToolRouter
from eiw.evidence.claim import ClaimManager
from eiw.governance.policy import PolicyEngine
from eiw.observability.tracing import get_tracer

tracer = get_tracer(__name__)


class AgentState(Enum):
    """States of the supervisor agent."""

    IDLE = "idle"
    RESOLVING_INTENT = "resolving_intent"
    RESOLVING_SEMANTICS = "resolving_semantics"
    PLANNING = "planning"
    INVESTIGATING = "investigating"
    VERIFYING = "verifying"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_CLARIFICATION = "requires_clarification"


@dataclass
class AgentContext:
    """Shared context for agent operations."""

    task_id: str
    question: str
    user_context: dict[str, Any]
    domain_id: str
    intent: IntentResult | None = None
    plan: AnalysisPlan | None = None
    current_step: int = 0
    observations: list[dict[str, Any]] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    state: AgentState = AgentState.IDLE
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "question": self.question,
            "user_context": self.user_context,
            "domain_id": self.domain_id,
            "intent": self.intent.to_context() if self.intent else None,
            "plan": self.plan.to_dict() if self.plan else None,
            "current_step": self.current_step,
            "observations": self.observations,
            "claims": self.claims,
            "evidence": self.evidence,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "state": self.state.value,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SupervisorAgent:
    """Supervisor Agent for Enterprise Data Agent.

    This is the central coordinator for the analysis workflow.
    It orchestrates:
    1. Intent Recognition
    2. Semantic Resolution
    3. Analysis Planning
    4. Tool Routing & Execution
    5. Hypothesis Testing
    6. Evidence Collection
    7. Verification
    8. Report Synthesis
    """

    def __init__(
        self,
        intent_resolver: IntentResolver | None = None,
        tool_router: ToolRouter | None = None,
        planner: AnalysisPlanner | None = None,
        hypothesis_manager: HypothesisManager | None = None,
        claim_manager: ClaimManager | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        """Initialize supervisor with required components."""
        self.intent_resolver = intent_resolver or IntentResolver()
        self.tool_router = tool_router or ToolRouter()
        self.planner = planner or AnalysisPlanner()
        self.hypothesis_manager = hypothesis_manager or HypothesisManager()
        self.claim_manager = claim_manager or ClaimManager()
        self.policy_engine = policy_engine or PolicyEngine()
        self._contexts: dict[str, AgentContext] = {}

    def create_task(
        self,
        question: str,
        user_context: dict[str, Any],
        domain_id: str = "default",
    ) -> AgentContext:
        """Create a new analysis task."""
        task_id = str(uuid.uuid4())
        context = AgentContext(
            task_id=task_id,
            question=question,
            user_context=user_context,
            domain_id=domain_id,
        )
        self._contexts[task_id] = context
        self._add_event(context, "TASK_CREATED", f"Analysis task {task_id} created")
        return context

    def run(self, context: AgentContext) -> AgentContext:
        """Execute the full analysis workflow."""
        with tracer.start_as_current_span("supervisor.run") as span:
            span.set_attribute("task_id", context.task_id)
            span.set_attribute("question", context.question)

            try:
                # Step 1: Intent Resolution
                context = self._resolve_intent(context)

                # Step 2: Policy Check
                context = self._check_policy(context)

                # If clarification needed, stop here
                if context.state == AgentState.REQUIRES_CLARIFICATION:
                    return context

                # Step 3: Semantic Resolution
                context = self._resolve_semantics(context)

                # Step 4: Planning
                context = self._create_plan(context)

                # Step 5: Investigation Loop
                context = self._investigate(context)

                # Step 6: Verification
                context = self._verify(context)

                # Step 7: Synthesis
                context = self._synthesize(context)

                context.state = AgentState.COMPLETED
                self._add_event(context, "TASK_COMPLETED", "Analysis completed successfully")

            except Exception as exc:
                context.state = AgentState.FAILED
                context.error = str(exc)
                self._add_event(context, "TASK_FAILED", str(exc))
                span.record_exception(exc)

            context.updated_at = datetime.now(UTC)
            return context

    def _resolve_intent(self, context: AgentContext) -> AgentContext:
        """Resolve the user's intent from natural language."""
        with tracer.start_as_current_span("supervisor.resolve_intent") as span:
            context.state = AgentState.RESOLVING_INTENT
            self._add_event(context, "INTENT_RESOLUTION_STARTED", "Starting intent resolution")

            intent = self.intent_resolver.resolve(context.question)
            context.intent = intent

            span.set_attribute("intent_type", intent.intent_type.value)
            span.set_attribute("confidence", intent.confidence)
            span.set_attribute("primary_metrics", intent.primary_metrics)

            if intent.requires_clarification:
                context.state = AgentState.REQUIRES_CLARIFICATION
                self._add_event(
                    context,
                    "CLARIFICATION_REQUIRED",
                    f"Clarification needed: {intent.clarification_questions}",
                )

            self._add_event(
                context,
                "INTENT_RESOLVED",
                f"Intent: {intent.intent_type.value}, confidence: {intent.confidence:.2f}",
            )

            return context

    def _check_policy(self, context: AgentContext) -> AgentContext:
        """Check if the user has permission for the requested analysis."""
        with tracer.start_as_current_span("supervisor.policy_check") as span:
            if not context.intent:
                return context

            # Check metric permissions
            denied_metrics = self.policy_engine.check_metric_access(
                context.user_context,
                context.intent.primary_metrics,
            )

            if denied_metrics:
                span.set_attribute("policy.denied_metrics", denied_metrics)
                self._add_event(
                    context,
                    "POLICY_DENIED",
                    f"Access denied for metrics: {denied_metrics}",
                )
                context.error = f"Access denied for metrics: {denied_metrics}"
                context.state = AgentState.FAILED
                return context

            self._add_event(context, "POLICY_PASSED", "User authorized for requested analysis")
            return context

    def _resolve_semantics(self, context: AgentContext) -> AgentContext:
        """Resolve business semantics from the semantic layer."""
        with tracer.start_as_current_span("supervisor.resolve_semantics") as span:
            context.state = AgentState.RESOLVING_SEMANTICS
            self._add_event(context, "SEMANTIC_RESOLUTION_STARTED", "Resolving business semantics")

            # This would integrate with the semantic layer to:
            # 1. Map user terms to metric IDs
            # 2. Resolve dimension definitions
            # 3. Check metric availability
            # 4. Get metric formulas and business rules

            # For now, we use the intent resolver's output
            # In production, this would query the semantic package
            if context.intent:
                span.set_attribute("metrics_resolved", context.intent.primary_metrics)
                span.set_attribute("dimensions_resolved", context.intent.dimensions)

            self._add_event(context, "SEMANTICS_RESOLVED", "Business semantics resolved")
            return context

    def _create_plan(self, context: AgentContext) -> AgentContext:
        """Create an analysis plan based on resolved intent."""
        with tracer.start_as_current_span("supervisor.create_plan") as span:
            context.state = AgentState.PLANNING
            self._add_event(context, "PLANNING_STARTED", "Creating analysis plan")

            if not context.intent:
                return context

            plan = self.planner.create_plan(
                task_id=context.task_id,
                intent=context.intent,
                user_context=context.user_context,
            )
            context.plan = plan

            # Create initial hypotheses
            context.hypotheses = self.hypothesis_manager.create_hypotheses(
                task_id=context.task_id,
                intent=context.intent,
            )

            span.set_attribute("plan_steps", len(plan.steps))
            span.set_attribute("hypothesis_count", len(context.hypotheses))

            self._add_event(
                context,
                "PLAN_CREATED",
                f"Plan created with {len(plan.steps)} steps and {len(context.hypotheses)} hypotheses",
            )

            return context

    def _investigate(self, context: AgentContext) -> AgentContext:
        """Execute the investigation loop."""
        with tracer.start_as_current_span("supervisor.investigate") as span:
            context.state = AgentState.INVESTIGATING

            if not context.plan:
                return context

            for step in context.plan.steps:
                context.current_step += 1

                with tracer.start_as_current_span(f"supervisor.step_{step.ordinal}") as step_span:
                    step_span.set_attribute("step_title", step.title)
                    step_span.set_attribute("step_purpose", step.purpose)

                    self._add_event(
                        context,
                        "STEP_STARTED",
                        f"Starting step {step.ordinal}: {step.title}",
                    )

                    # Route to appropriate tools
                    routing = self.tool_router.route(
                        intent_type=step.purpose,
                        metrics=context.intent.primary_metrics if context.intent else [],
                        dimensions=context.intent.dimensions if context.intent else [],
                        requires_nl2sql=context.intent.requires_nl2sql if context.intent else False,
                    )

                    # Execute tools and collect observations
                    observations = self._execute_step(context, step, routing)

                    # Update hypotheses based on observations
                    for obs in observations:
                        self.hypothesis_manager.update_with_observation(
                            context.hypotheses,
                            obs,
                        )

                    # Check if we should stop
                    if self._should_stop(context):
                        span.set_attribute("stop_reason", "budget_exceeded")
                        break

                    self._add_event(
                        context,
                        "STEP_COMPLETED",
                        f"Step {step.ordinal} completed with {len(observations)} observations",
                    )

            return context

    def _execute_step(
        self,
        context: AgentContext,
        step: Any,
        routing: RoutingDecision,
    ) -> list[dict[str, Any]]:
        """Execute a single analysis step."""
        observations: list[dict[str, Any]] = []

        # In production, this would:
        # 1. Call the appropriate tool (metric_query, nl2sql, etc.)
        # 2. Execute the query
        # 3. Validate results
        # 4. Create observations

        # For now, we create a placeholder observation
        obs_id = str(uuid.uuid4())
        observation = {
            "observation_id": obs_id,
            "task_id": context.task_id,
            "step_id": step.step_id if hasattr(step, "step_id") else str(step.ordinal),
            "tool": routing.primary_tool,
            "statement": f"Executed {routing.primary_tool} for: {step.title}",
            "timestamp": datetime.now(UTC).isoformat(),
            "routing_reasoning": routing.reasoning,
        }
        observations.append(observation)
        context.observations.append(observation)

        return observations

    def _should_stop(self, context: AgentContext) -> bool:
        """Determine if the investigation should stop."""
        # Check budget
        if context.current_step >= (context.plan.max_steps if context.plan else 10):
            return True

        # Check if all hypotheses are resolved
        unresolved = [h for h in context.hypotheses if not h.is_resolved]
        return bool(len(unresolved) == 0 and context.hypotheses)

    def _verify(self, context: AgentContext) -> AgentContext:
        """Verify claims against evidence."""
        with tracer.start_as_current_span("supervisor.verify"):
            context.state = AgentState.VERIFYING
            self._add_event(context, "VERIFICATION_STARTED", "Verifying claims")

            # Verify each claim against evidence
            for claim in context.claims:
                is_verified = self.claim_manager.verify_claim(claim, context.evidence)
                claim["verified"] = is_verified
                claim["verified_at"] = datetime.now(UTC).isoformat()

            self._add_event(
                context,
                "VERIFICATION_COMPLETED",
                f"Verified {len(context.claims)} claims",
            )

            return context

    def _synthesize(self, context: AgentContext) -> AgentContext:
        """Synthesize findings into final report."""
        with tracer.start_as_current_span("supervisor.synthesize"):
            context.state = AgentState.SYNTHESIZING
            self._add_event(context, "SYNTHESIS_STARTED", "Synthesizing final report")

            # Create summary
            summary = {
                "task_id": context.task_id,
                "question": context.question,
                "intent": context.intent.intent_type.value if context.intent else "unknown",
                "metrics_analyzed": context.intent.primary_metrics if context.intent else [],
                "observations_collected": len(context.observations),
                "claims_made": len(context.claims),
                "evidence_collected": len(context.evidence),
                "hypotheses_tested": len(context.hypotheses),
                "steps_executed": context.current_step,
                "key_findings": [c.get("statement", "") for c in context.claims],
            }

            context.summary = summary

            self._add_event(
                context,
                "SYNTHESIS_COMPLETED",
                f"Report synthesized with {len(context.claims)} key findings",
            )

            return context

    def _add_event(
        self,
        context: AgentContext,
        event_type: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Add an event to the context."""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            "state": context.state.value,
            **kwargs,
        }
        context.events.append(event)

    def get_context(self, task_id: str) -> AgentContext | None:
        """Get task context by ID."""
        return self._contexts.get(task_id)

    def resume(self, task_id: str) -> AgentContext | None:
        """Resume a paused or partially completed task."""
        context = self.get_context(task_id)
        if not context:
            return None

        # Resume from where we left off
        return self.run(context)
