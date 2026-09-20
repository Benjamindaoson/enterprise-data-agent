"""Agent Runtime - Main orchestrator.

This module provides:
- Agent initialization
- End-to-end analysis execution
- Session management
- Result formatting
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from eiw.agent.provider import ModelProvider, DeterministicProvider, ProviderConfig, create_provider
from eiw.agent.intent import IntentResolver, ResolvedBusinessIntent, IntentResolutionResult
from eiw.agent.planner import AnalysisPlanner, AnalysisPlan, create_analysis_planner
from eiw.agent.supervisor import (
    Supervisor, AnalysisTask, TaskStatus, create_supervisor,
    SupervisorDecision
)
from eiw.agent.state import DurableStateManager, create_state_manager, TaskStateBuilder
from eiw.agent.tools import ToolRegistry, create_tool_registry, ToolExecutionContext
from eiw.agent.governance import (
    AccessControl, GovernanceConfig, create_governance_config,
    create_demo_session, create_demo_personas, Role
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "agent_runtime")


# =============================================================================
# Agent Result Types
# =============================================================================


class AnalysisStatus(str, Enum):
    """Status of an analysis."""

    PENDING = "pending"
    INTENT_RESOLVING = "intent_resolving"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CLARIFICATION_NEEDED = "clarification_needed"


class AgentResult(BaseModel):
    """Result of agent analysis."""

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(description="Task identifier")
    status: AnalysisStatus = Field(description="Analysis status")
    question: str = Field(description="Original question")

    # Intent
    intent: dict[str, Any] | None = Field(default=None)
    clarification_needed: bool = Field(default=False)
    clarification_questions: list[dict[str, Any]] = Field(default_factory=list)

    # Plan
    plan_steps: list[dict[str, Any]] = Field(default_factory=list)

    # Results
    observations: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    final_answer: str = Field(default="")

    # Metadata
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = Field(default=None)
    duration_ms: int = Field(default=0)
    steps_executed: int = Field(default=0)
    steps_failed: int = Field(default=0)

    # Error
    error: str | None = Field(default=None)


# =============================================================================
# Agent Runtime
# =============================================================================


class AgentRuntime:
    """Main agent runtime.

    This runtime:
    1. Resolves user intent
    2. Creates analysis plan
    3. Executes through supervisor
    4. Manages state and checkpoints
    5. Returns structured results
    """

    def __init__(
        self,
        provider: ModelProvider | None = None,
        enable_checkpoint: bool = True,
        governance_config: GovernanceConfig | None = None,
        nl2sql_service: Any | None = None,
    ):
        """Initialize agent runtime.

        Args:
            provider: Model provider
            enable_checkpoint: Enable state checkpoints
            governance_config: Governance configuration
            nl2sql_service: Optional NL2SQL service
        """
        # Initialize components
        self._provider = provider or create_provider()
        self._intent_resolver = IntentResolver(provider=self._provider)
        self._analysis_planner = create_analysis_planner(provider=self._provider)
        self._supervisor = create_supervisor(provider=self._provider)
        self._state_manager = create_state_manager() if enable_checkpoint else None
        self._access_control = AccessControl()
        self._governance_config = governance_config or create_governance_config()

        # Tool registry
        self._tool_registry = create_tool_registry(nl2sql_service)
        self._register_supervisor_tools()

        # Sessions
        self._sessions: dict[str, Any] = {}

        logger.info("Agent runtime initialized")

    def _register_supervisor_tools(self) -> None:
        """Register tools with supervisor."""
        def create_handler(name: str):
            """Create a handler function for a tool.

            Uses default argument to capture name value at definition time.
            """
            async def handler(**kwargs):
                ctx = ToolExecutionContext(
                    task_id=kwargs.get("_task_id", ""),
                    step_id=kwargs.get("_step_id", ""),
                )
                # Remove internal params
                clean_params = {k: v for k, v in kwargs.items() if not k.startswith("_")}
                result = await self._tool_registry.execute(name, clean_params, ctx)
                return result.data if result.success else {"error": result.error}
            return handler

        # Register each tool with its handler
        for tool in self._tool_registry.list_all():
            self._supervisor.register_tool(tool.category, create_handler(tool.name))

    async def analyze(
        self,
        question: str,
        domain: str | None = None,
        session: Any | None = None,
        checkpoint_id: str | None = None,
    ) -> AgentResult:
        """Run an analysis.

        Args:
            question: User question
            domain: Business domain
            session: Optional user session
            checkpoint_id: Optional checkpoint to resume from

        Returns:
            Analysis result
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()

        result = AgentResult(
            task_id=task_id,
            status=AnalysisStatus.PENDING,
            question=question,
            started_at=start_time,
        )

        with trace_span("agent.analyze", {
            "task_id": task_id,
            "question_length": len(question),
            "domain": domain,
        }):
            try:
                # Step 1: Resolve intent
                result.status = AnalysisStatus.INTENT_RESOLVING
                intent_result = await self._intent_resolver.resolve(
                    question=question,
                    domain=domain,
                    user_roles=self._get_user_roles(session),
                )

                if not intent_result.success:
                    if intent_result.clarification_needed:
                        result.status = AnalysisStatus.CLARIFICATION_NEEDED
                        result.clarification_needed = True
                        result.clarification_questions = [
                            q.model_dump() for q in intent_result.clarification_questions
                        ]
                        return result

                result.intent = intent_result.intent.model_dump() if intent_result.intent else None

                # Step 2: Create plan
                result.status = AnalysisStatus.PLANNING
                intent_obj = intent_result.intent
                if intent_obj and hasattr(intent_obj, 'analysis_type'):
                    analysis_type = intent_obj.analysis_type.value if hasattr(intent_obj.analysis_type, 'value') else str(intent_obj.analysis_type)
                else:
                    analysis_type = "descriptive"
                plan = await self._analysis_planner.create_plan(
                    intent=intent_result.intent,
                    question=question,
                    domain=domain or "general",
                )
                result.plan_steps = [s.to_trace_dict() for s in plan.steps]

                # Step 3: Create task
                task = AnalysisTask(
                    task_id=task_id,
                    question=question,
                    domain=domain or "",
                    total_budget_ms=plan.total_budget_ms,
                    intent=result.intent,
                )

                # Step 4: Execute through supervisor
                result.status = AnalysisStatus.EXECUTING
                final_task = await self._supervisor.run(task, intent_result.intent, plan)

                # Step 5: Build result
                result.status = AnalysisStatus.COMPLETED
                result.observations = final_task.observations
                result.claims = final_task.claims
                result.steps_executed = len(final_task.completed_steps)
                result.steps_failed = len(final_task.failed_steps)

                # Generate answer
                result.final_answer = self._generate_answer(result)

                # Save checkpoint
                if self._state_manager:
                    self._state_manager.save_state(task_id, {
                        "result": result.model_dump(),
                        "plan": plan.to_trace_dict(),
                    })

            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                result.status = AnalysisStatus.FAILED
                result.error = str(e)

            finally:
                result.completed_at = datetime.now()
                result.duration_ms = int((result.completed_at - start_time).total_seconds() * 1000)

        return result

    async def resume(self, task_id: str) -> AgentResult | None:
        """Resume a task from checkpoint.

        Args:
            task_id: Task to resume

        Returns:
            Resumed result or None
        """
        if not self._state_manager:
            return None

        state = self._state_manager.load_state(task_id)
        if not state:
            return None

        result_data = state.get("result", {})
        result = AgentResult(**result_data)

        # Resume supervisor
        # (simplified - full implementation would restore full state)

        return result

    def _get_user_roles(self, session: Any | None) -> list[str]:
        """Get user roles from session."""
        if not session:
            return []
        return getattr(session, "roles", [])

    def _generate_answer(self, result: AgentResult) -> str:
        """Generate natural language answer.

        Args:
            result: Analysis result

        Returns:
            Natural language answer
        """
        if not result.observations:
            return "No observations were recorded during analysis."

        # Build answer from observations
        lines = ["Based on my analysis:\n"]

        for i, obs in enumerate(result.observations[:3], 1):
            content = obs.get("content", "")
            if content:
                lines.append(f"{i}. {content[:200]}")

        if result.claims:
            lines.append(f"\nKey findings:")
            for claim in result.claims[:2]:
                lines.append(f"- {claim.get('statement', '')}")

        return "\n".join(lines)

    def create_session(self, user_id: str) -> Any:
        """Create a session for a user.

        Args:
            user_id: User ID

        Returns:
            Session object
        """
        personas = create_demo_personas()
        user = personas.get(user_id)
        if not user:
            return None

        session = create_demo_session(user)
        self._sessions[session.session_id] = session
        return session

    def get_audit_log(self, session: Any) -> list[dict[str, Any]]:
        """Get audit log.

        Args:
            session: User session

        Returns:
            Audit log entries
        """
        return self._access_control.get_audit_log(user_id=session.user_id)


# =============================================================================
# Factory
# =============================================================================


def create_agent_runtime(
    provider_type: str = "deterministic",
    api_key: str | None = None,
    enable_checkpoint: bool = True,
    nl2sql_service: Any | None = None,
) -> AgentRuntime:
    """Create agent runtime.

    Args:
        provider_type: Provider type
        api_key: API key for real providers
        enable_checkpoint: Enable checkpoints
        nl2sql_service: NL2SQL service

    Returns:
        Agent runtime
    """
    config = ProviderConfig(
        provider_type=provider_type,
        api_key=api_key,
    )
    provider = create_provider(config)

    return AgentRuntime(
        provider=provider,
        enable_checkpoint=enable_checkpoint,
        nl2sql_service=nl2sql_service,
    )


# =============================================================================
# CLI Entry Point
# =============================================================================


async def run_cli():
    """Run the agent CLI."""
    runtime = create_agent_runtime()

    print("Enterprise Data Agent v2.0")
    print("Enter your question (or 'quit' to exit):\n")

    while True:
        try:
            question = input("> ")
            if question.lower() in ("quit", "exit", "q"):
                break

            if not question.strip():
                continue

            result = await runtime.analyze(question)

            print(f"\nStatus: {result.status.value}")
            print(f"Duration: {result.duration_ms}ms")
            print(f"\n{result.final_answer}\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\nGoodbye!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_cli())
