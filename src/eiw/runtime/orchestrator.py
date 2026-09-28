"""Canonical application runtime for the Enterprise Data Agent.

This module is the single application-layer entry point used by the FastAPI
surface. It deliberately composes the existing verified analytical workflow,
business-operations planner, typed Skill registry and layered memory contracts
instead of creating another parallel Agent implementation.

The runtime owns application-level orchestration. Domain services keep ownership
of deterministic execution and persistence details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from eiw.business.models import BusinessTaskRequest, BusinessTaskResponse
from eiw.business.operations import BusinessOperationsService
from eiw.production.persistence import ProductionStore
from eiw.runtime.domain import DomainEventCallback, DomainRuntime
from eiw.runtime.memory import MemoryKind, MemoryRecord, MemoryStore
from eiw.runtime.skills import SkillRegistry, default_skill_registry
from eiw.workspace.analysis import AnalysisService
from eiw.workspace.store import WorkspaceStore


@dataclass(slots=True)
class RuntimeTraceEvent:
    """Observable runtime event; never stores private chain-of-thought."""

    event_type: str
    message: str
    task_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "message": self.message,
            "task_id": self.task_id,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }


class BusinessAgentRuntime:
    """Canonical application runtime.

    Responsibilities:
    - expose one entry point for analysis and business-operation requests;
    - keep runtime metadata and trace semantics consistent across API lanes;
    - reuse the existing AnalysisService and BusinessOperationsService;
    - record lightweight episodic memory from completed application tasks;
    - make deterministic-vs-model-driven boundaries explicit.

    This class does not duplicate NL2SQL, analytical execution, governance or
    persistence logic. Those remain owned by their existing services.
    """

    RUNTIME_VERSION = "1.0.0"
    CANONICAL_PATH = (
        "BusinessGoal -> Runtime -> Skill/AnalyticalLane -> GovernedTool -> "
        "Observation/Evidence -> Verification -> Result"
    )

    def __init__(
        self,
        *,
        analysis_service: AnalysisService | None,
        business_service: BusinessOperationsService | None = None,
        skills: SkillRegistry | None = None,
        memory: MemoryStore | None = None,
        production_store: ProductionStore | None = None,
        domain_runtimes: list[DomainRuntime] | None = None,
    ) -> None:
        self.analysis_service = analysis_service
        self.business_service = business_service or BusinessOperationsService()
        self.skills = skills or default_skill_registry()
        self.memory = memory or MemoryStore()
        self.production_store = production_store
        self._events: list[RuntimeTraceEvent] = []
        self._trajectory_steps: dict[str, int] = {}
        self._domain_runtimes: dict[str, DomainRuntime] = {}
        for domain_runtime in domain_runtimes or []:
            self.register_domain(domain_runtime)

    def capabilities(self) -> dict[str, Any]:
        """Return capabilities from the runtime that actually serves requests."""

        return {
            "runtime": {
                "name": "BusinessAgentRuntime",
                "version": self.RUNTIME_VERSION,
                "canonical_path": self.CANONICAL_PATH,
                "analysis_lane": "deterministic_semantic_analytics",
                "agent_learning_lane": "offline_sft_grpo_evaluation",
                "external_writes": "proposal_or_approval_gated",
            },
            "domains": {
                domain_id: runtime.capabilities()
                for domain_id, runtime in sorted(self._domain_runtimes.items())
            },
            "business_scenarios": [
                "ANALYTICS",
                "MARKETING_BUDGET",
                "SALES_EXPANSION",
                "MONETIZATION",
            ],
            "skills": [
                {
                    "skill_id": skill.skill_id,
                    "version": skill.version,
                    "description": skill.description,
                    "tools": list(skill.tool_dependencies),
                    "permissions": list(skill.permissions),
                    "tags": list(skill.tags),
                }
                for skill in self.skills.list()
            ],
            "public_reference_limits": {
                "external_writes": "proposal/dry-run only",
                "post_training": (
                    "Small-policy SFT/GRPO is verified in CI; the real open-weight "
                    "LLM path is implemented but requires an external/self-hosted run "
                    "before gain numbers are claimed."
                ),
                "real_campaign_crm_integrations": False,
            },
        }

    def analyze(
        self,
        question: str,
        user_context: dict[str, Any],
        *,
        lineage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the canonical governed analytical lane."""

        if self.analysis_service is None:
            raise RuntimeError("The generic analytical lane is not configured")

        invocation_id = f"run_{uuid4().hex[:12]}"
        self._record(
            "RUNTIME_STARTED",
            "Canonical analytical runtime started.",
            payload={"invocation_id": invocation_id},
        )

        result = self.analysis_service.create(
            question,
            user_context,
            lineage=lineage,
        )
        task_id = str(result.get("task_id", "")) or None

        runtime_metadata = {
            "runtime_name": "BusinessAgentRuntime",
            "runtime_version": self.RUNTIME_VERSION,
            "invocation_id": invocation_id,
            "canonical_path": self.CANONICAL_PATH,
            "lane": "deterministic_semantic_analytics",
        }
        result["runtime"] = runtime_metadata
        # AnalysisService owns the workspace store; persist the runtime envelope
        # back into the same task record instead of maintaining parallel state.
        workspace_store = getattr(self.analysis_service, "store", None)
        if workspace_store is not None:
            workspace_store.put_task(result)

        self._record(
            "RUNTIME_COMPLETED",
            "Canonical analytical runtime completed.",
            task_id=task_id,
            payload={
                "invocation_id": invocation_id,
                "state": result.get("state"),
                "claim_count": len(result.get("claims", [])),
                "evidence_count": len(result.get("evidence", [])),
            },
        )
        if task_id:
            self._remember_analysis(task_id, question, result)
        return result

    def follow_up(
        self,
        *,
        parent_task_id: str,
        question: str,
        referenced_evidence_ids: list[str],
        store: WorkspaceStore,
    ) -> dict[str, Any]:
        """Create a new child task while preserving explicit evidence lineage."""

        parent = store.get_task(parent_task_id)
        if parent is None:
            raise KeyError(parent_task_id)

        lineage = {
            "parent_task_id": parent_task_id,
            "reused_evidence_ids": referenced_evidence_ids,
            "parent_context_version": parent.get("resolved_context", {}).get(
                "context_version"
            ),
        }
        return self.analyze(
            question,
            parent.get("user_context", {}),
            lineage=lineage,
        )

    def plan_business_task(
        self,
        request: BusinessTaskRequest,
    ) -> BusinessTaskResponse:
        """Plan a governed business-operation task through the same runtime."""

        self._record(
            "BUSINESS_TASK_STARTED",
            "Business-operation planning started.",
            payload={"scenario": request.scenario.value},
        )
        response = self.business_service.plan(request)
        self._record(
            "BUSINESS_TASK_PLANNED",
            "Business-operation planning completed.",
            task_id=str(response.task_id),
            payload={
                "scenario": response.scenario.value,
                "status": response.status,
                "capabilities_used": response.capabilities_used,
            },
        )
        self.memory.put(
            MemoryRecord(
                key=f"business-task:{response.task_id}",
                kind=MemoryKind.EPISODIC,
                task_id=str(response.task_id),
                value={
                    "scenario": response.scenario.value,
                    "status": response.status,
                    "capabilities_used": response.capabilities_used,
                },
            )
        )
        return response

    def register_domain(self, runtime: DomainRuntime, *, replace: bool = False) -> None:
        """Register one vertical under the single canonical application runtime."""

        domain_id = runtime.domain_id.strip()
        if not domain_id:
            raise ValueError("domain runtime must expose a non-empty domain_id")
        existing = self._domain_runtimes.get(domain_id)
        if existing is not None and existing is not runtime and not replace:
            raise ValueError(f"domain runtime already registered: {domain_id}")
        self._domain_runtimes[domain_id] = runtime

    def domain_runtime(self, domain_id: str) -> DomainRuntime:
        """Return a registered vertical or fail closed."""

        try:
            return self._domain_runtimes[domain_id]
        except KeyError as exc:
            raise KeyError(f"unknown domain runtime: {domain_id}") from exc

    def analyze_domain(
        self,
        domain_id: str,
        request: Any,
        *,
        on_event: DomainEventCallback | None = None,
    ) -> Any:
        """Route a vertical request through BusinessAgentRuntime before delegation."""

        runtime = self.domain_runtime(domain_id)
        invocation_id = f"domain_{uuid4().hex[:12]}"
        self._record(
            "DOMAIN_RUNTIME_STARTED",
            f"Domain runtime started: {domain_id}.",
            payload={"domain_id": domain_id, "invocation_id": invocation_id},
        )
        result = runtime.analyze(request, on_event=on_event)
        task_id = getattr(result, "task_id", None)
        status = getattr(result, "status", None)
        if isinstance(result, dict):
            task_id = task_id or result.get("task_id")
            status = status or result.get("status") or result.get("state")
        self._record(
            "DOMAIN_RUNTIME_COMPLETED",
            f"Domain runtime completed: {domain_id}.",
            task_id=str(task_id) if task_id else None,
            payload={
                "domain_id": domain_id,
                "invocation_id": invocation_id,
                "status": status,
            },
        )
        return result

    def events(self, *, task_id: str | None = None) -> list[dict[str, Any]]:
        """Return observable runtime events, optionally scoped to one task.

        When PostgreSQL persistence is configured and a task is requested, the
        durable trajectory is authoritative so events remain available after a
        process restart.
        """

        if self.production_store is not None and task_id is not None:
            rows = self.production_store.load_trajectory(f"runtime:{task_id}")
            if rows:
                return [
                    dict(row.get("payload", {}))
                    for row in rows
                    if row.get("payload")
                ]

        selected = [
            event
            for event in self._events
            if task_id is None or event.task_id == task_id
        ]
        return [event.as_dict() for event in selected]

    def _remember_analysis(
        self,
        task_id: str,
        question: str,
        result: dict[str, Any],
    ) -> None:
        self.memory.put(
            MemoryRecord(
                key=f"analysis:{task_id}",
                kind=MemoryKind.EPISODIC,
                task_id=task_id,
                value={
                    "question": question,
                    "state": result.get("state"),
                    "claim_ids": [
                        claim.get("claim_id")
                        for claim in result.get("claims", [])
                        if claim.get("claim_id")
                    ],
                    "evidence_ids": [
                        evidence.get("evidence_id")
                        for evidence in result.get("evidence", [])
                        if evidence.get("evidence_id")
                    ],
                },
            )
        )

    def _record(
        self,
        event_type: str,
        message: str,
        *,
        task_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = RuntimeTraceEvent(
            event_type=event_type,
            message=message,
            task_id=task_id,
            payload=payload or {},
        )
        self._events.append(event)

        if self.production_store is not None and task_id is not None:
            step_index = self._trajectory_steps.get(task_id, 0)
            self.production_store.append_trajectory_event(
                trajectory_id=f"runtime:{task_id}",
                task_id=task_id,
                step_index=step_index,
                payload=event.as_dict(),
            )
            self._trajectory_steps[task_id] = step_index + 1
