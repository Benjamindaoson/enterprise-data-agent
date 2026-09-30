"""Canonical application runtime for the Enterprise Data Agent.

This module is the single application-layer entry point used by the FastAPI
surface. It deliberately composes the existing verified analytical workflow,
business-operations planner, typed Skill registry and layered memory contracts
instead of creating another parallel Agent implementation.

The runtime owns application-level orchestration. Domain services keep ownership
of deterministic execution and persistence details.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from eiw.business.models import BusinessTaskRequest, BusinessTaskResponse
from eiw.business.operations import BusinessOperationsService
from eiw.ontology.runtime import OntologyRuntime
from eiw.production.persistence import ProductionStore
from eiw.runtime.domain import DomainRuntime
from eiw.runtime.long_term_memory import LongTermMemoryBackend, LongTermMemoryItem
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
        long_term_memory: LongTermMemoryBackend | None = None,
        production_store: ProductionStore | None = None,
        domains: list[DomainRuntime] | None = None,
        ontology_runtime: OntologyRuntime | None = None,
    ) -> None:
        self.analysis_service = analysis_service
        self.business_service = business_service or BusinessOperationsService()
        self.skills = skills or default_skill_registry()
        self.memory = memory or MemoryStore()
        self.long_term_memory = long_term_memory
        self.production_store = production_store
        self.ontology_runtime = ontology_runtime
        self._events: list[RuntimeTraceEvent] = []
        self._trajectory_steps: dict[str, int] = {}
        self._domains: dict[str, DomainRuntime] = {}
        for domain in domains or []:
            self.register_domain(domain)

    def register_domain(self, domain: DomainRuntime) -> None:
        """Register one domain adapter under the canonical application runtime."""

        if domain.domain_id in self._domains:
            raise ValueError(f"domain runtime already registered: {domain.domain_id}")
        self._domains[domain.domain_id] = domain

    def has_domain(self, domain_id: str) -> bool:
        return domain_id in self._domains

    def browse_ontology(
        self,
        ontology_id: str,
        query: str,
        *,
        semantic_types: set[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        if self.ontology_runtime is None:
            return []
        return [
            item.model_dump(mode="json")
            for item in self.ontology_runtime.browse(
                ontology_id,
                query,
                semantic_types=semantic_types,
                limit=limit,
            )
        ]

    def resolve_ontology(
        self,
        ontology_id: str,
        term_ids: list[str],
        *,
        include_evidence: bool = True,
    ) -> dict[str, Any] | None:
        if self.ontology_runtime is None:
            return None
        return self.ontology_runtime.resolve(
            ontology_id,
            term_ids,
            include_evidence=include_evidence,
        ).model_dump(mode="json")

    def domain_runtime(self, domain_id: str) -> DomainRuntime:
        try:
            return self._domains[domain_id]
        except KeyError as exc:
            raise KeyError(f"unknown domain runtime: {domain_id}") from exc

    def analyze_domain(
        self,
        domain_id: str,
        request: object,
        *,
        on_event: Callable[[object], None] | None = None,
    ) -> object:
        """Route a domain request through the single application runtime."""

        domain = self.domain_runtime(domain_id)
        memory_scope = self._domain_memory_scope(domain_id, request)
        question = getattr(request, "question", None)
        if self.long_term_memory is not None and isinstance(question, str):
            memories = self._recall_long_term(memory_scope, question)
            if (
                memories
                and hasattr(request, "model_copy")
                and hasattr(request, "memory_context")
            ):
                request = request.model_copy(
                    update={"memory_context": [item.text for item in memories[:8]]}
                )

        self._record(
            "DOMAIN_RUNTIME_STARTED",
            f"Domain runtime started: {domain_id}.",
            payload={"domain_id": domain_id},
        )
        try:
            response = domain.analyze(request, on_event=on_event)
        except Exception as exc:
            self._record(
                "DOMAIN_RUNTIME_FAILED",
                f"Domain runtime failed: {domain_id}.",
                payload={
                    "domain_id": domain_id,
                    "error_type": type(exc).__name__,
                },
            )
            raise

        task_id_value = (
            response.get("task_id")
            if isinstance(response, dict)
            else getattr(response, "task_id", None)
        )
        task_id = str(task_id_value) if task_id_value else None
        self._record(
            "DOMAIN_RUNTIME_COMPLETED",
            f"Domain runtime completed: {domain_id}.",
            task_id=task_id,
            payload={"domain_id": domain_id},
        )
        if self.long_term_memory is not None and isinstance(question, str):
            self._retain_domain_result(
                memory_scope,
                domain_id=domain_id,
                question=question,
                response=response,
                task_id=task_id,
            )
        return response

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
            "ontology": (
                self.ontology_runtime.manifests()
                if self.ontology_runtime is not None
                else {}
            ),
            "long_term_memory": {
                "configured": self.long_term_memory is not None,
                "backend": (
                    self.long_term_memory.name
                    if self.long_term_memory is not None
                    else None
                ),
                "operations": (
                    ["recall", "retain", "reflect"]
                    if self.long_term_memory is not None
                    else []
                ),
            },
            "domains": {
                domain_id: domain.capabilities()
                for domain_id, domain in sorted(self._domains.items())
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
            raise RuntimeError("generic analysis service is not configured")

        invocation_id = f"run_{uuid4().hex[:12]}"
        self._record(
            "RUNTIME_STARTED",
            "Canonical analytical runtime started.",
            payload={"invocation_id": invocation_id},
        )

        memory_scope = self._user_memory_scope(user_context)
        enriched_context = dict(user_context)
        if self.long_term_memory is not None:
            memories = self._recall_long_term(memory_scope, question)
            if memories:
                enriched_context["long_term_memory"] = [
                    item.as_context() for item in memories
                ]

        result = self.analysis_service.create(
            question,
            enriched_context,
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
            self._retain_analysis_long_term(
                memory_scope,
                task_id=task_id,
                question=question,
                result=result,
            )
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
        if self.long_term_memory is not None:
            self._retain_long_term(
                f"business:{response.scenario.value.lower()}",
                json.dumps(
                    {
                        "question": request.question,
                        "status": response.status,
                        "capabilities_used": response.capabilities_used,
                    },
                    ensure_ascii=False,
                ),
                context="completed business task",
                tags=("business-task", response.scenario.value.lower()),
            )
        return response

    def reflect_long_term_memory(
        self,
        query: str,
        *,
        user_context: dict[str, Any] | None = None,
        domain_id: str | None = None,
    ) -> str:
        if self.long_term_memory is None:
            raise RuntimeError("long-term memory is not configured")
        scope = (
            f"domain:{domain_id}"
            if domain_id
            else self._user_memory_scope(user_context or {})
        )
        return self.long_term_memory.reflect(scope, query)

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

    @staticmethod
    def _user_memory_scope(user_context: dict[str, Any]) -> str:
        tenant = str(user_context.get("tenant_id") or "default")
        user = str(user_context.get("user_id") or "anonymous")
        return f"tenant:{tenant}:user:{user}"

    @staticmethod
    def _domain_memory_scope(domain_id: str, request: object) -> str:
        tenant = str(getattr(request, "tenant_id", None) or "default")
        user = str(getattr(request, "user_id", None) or "anonymous")
        return f"domain:{domain_id}:tenant:{tenant}:user:{user}"

    def record_feedback(
        self,
        *,
        task_id: str,
        rating: int,
        comment: str,
        user_context: dict[str, Any],
    ) -> None:
        """Retain explicit user/expert feedback as cross-task learning evidence."""

        if self.long_term_memory is None:
            return
        self._retain_long_term(
            self._user_memory_scope(user_context),
            json.dumps(
                {"task_id": task_id, "rating": rating, "comment": comment},
                ensure_ascii=False,
            ),
            context="explicit user or expert feedback",
            tags=("feedback", "analysis", f"rating:{rating}"),
        )

    def _recall_long_term(
        self,
        scope: str,
        question: str,
    ) -> list[LongTermMemoryItem]:
        if self.long_term_memory is None:
            return []
        try:
            items = self.long_term_memory.recall(scope, question)
        except Exception as exc:
            self._record(
                "LONG_TERM_MEMORY_UNAVAILABLE",
                "Long-term memory recall failed; continuing without recalled context.",
                payload={
                    "backend": self.long_term_memory.name,
                    "error_type": type(exc).__name__,
                },
            )
            return []
        self._record(
            "LONG_TERM_MEMORY_RECALLED",
            f"Recalled {len(items)} long-term memories.",
            payload={
                "backend": self.long_term_memory.name,
                "bank_id": self.long_term_memory.bank_id(scope),
                "memory_count": len(items),
            },
        )
        return items

    def _retain_long_term(
        self,
        scope: str,
        content: str,
        *,
        context: str,
        tags: tuple[str, ...],
    ) -> None:
        if self.long_term_memory is None:
            return
        try:
            self.long_term_memory.retain(
                scope,
                content,
                context=context,
                tags=tags,
            )
        except Exception as exc:
            self._record(
                "LONG_TERM_MEMORY_UNAVAILABLE",
                "Long-term memory retain failed; core task result remains valid.",
                payload={
                    "backend": self.long_term_memory.name,
                    "error_type": type(exc).__name__,
                },
            )

    def _retain_analysis_long_term(
        self,
        scope: str,
        *,
        task_id: str,
        question: str,
        result: dict[str, Any],
    ) -> None:
        self._retain_long_term(
            scope,
            json.dumps(
                {
                    "task_id": task_id,
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
                ensure_ascii=False,
            ),
            context="completed enterprise analysis",
            tags=("analysis", "completed"),
        )

    def _retain_domain_result(
        self,
        scope: str,
        *,
        domain_id: str,
        question: str,
        response: object,
        task_id: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "domain_id": domain_id,
            "task_id": task_id,
            "question": question,
        }
        if hasattr(response, "model_dump"):
            rendered = response.model_dump(mode="json")
            payload["status"] = rendered.get("status")
            payload["insights"] = [
                item.get("title")
                for item in rendered.get("insights", [])[:8]
                if item.get("title")
            ]
            payload["skills"] = sorted(
                {
                    skill
                    for workstream in rendered.get("workstreams", [])
                    for skill in workstream.get("metadata", {}).get(
                        "selected_skills",
                        [],
                    )
                }
            )
        self._retain_long_term(
            scope,
            json.dumps(payload, ensure_ascii=False),
            context=f"completed {domain_id} domain analysis",
            tags=("analysis", domain_id, "experience"),
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
