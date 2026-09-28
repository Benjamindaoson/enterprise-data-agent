"""Retail domain adapter hosted by BusinessAgentRuntime.

The application-level canonical runtime is BusinessAgentRuntime. RetailBARuntime
is intentionally an internal domain agent that owns the retail investigation
graph, specialist workers, insight mining and report construction.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from eiw.ontology.runtime import OntologyRuntime
from eiw.retail.data import RetailDataEngine
from eiw.retail.guard import RequestDisposition, RetailRequestGuard
from eiw.retail.models import RetailAnalysisRequest, RetailAnalysisResponse, RuntimeEvent
from eiw.retail.runtime import EventCallback, RetailBARuntime
from eiw.retail.specialist_policy import OpenAICompatibleSpecialistPolicy
from eiw.retail.supervisor import OpenAICompatibleSupervisor
from eiw.runtime.domain import DomainClarificationRequired, DomainRequestRejected


class RetailDomainRuntime:
    """Domain adapter between BusinessAgentRuntime and the Retail BA Agent."""

    domain_id = "retail"

    def __init__(
        self,
        agent: RetailBARuntime,
        *,
        guard: RetailRequestGuard | None = None,
    ) -> None:
        self.agent = agent
        self.guard = guard or RetailRequestGuard()

    @property
    def data(self) -> RetailDataEngine:
        return self.agent.data

    def capabilities(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "application_runtime": "BusinessAgentRuntime",
            "domain_runtime": "RetailDomainRuntime",
            "domain_agent": "RetailBARuntime",
            "dataset": self.data.status(),
            "execution": (
                "real-data"
                if not self.data.label.startswith("retail-demo")
                else "deterministic-demo"
            ),
            "request_guard": "RetailRequestGuard-v1",
        }

    def analyze(
        self,
        request: object,
        *,
        on_event: Callable[[object], None] | None = None,
    ) -> RetailAnalysisResponse:
        if not isinstance(request, RetailAnalysisRequest):
            raise TypeError("RetailDomainRuntime requires RetailAnalysisRequest")

        decision = self.guard.assess(request, self.data)
        if decision.disposition == RequestDisposition.REJECT:
            raise DomainRequestRejected(decision.reason, code=decision.code)
        if decision.disposition == RequestDisposition.CLARIFY:
            raise DomainClarificationRequired(decision.reason, code=decision.code)

        callback = cast(EventCallback | None, on_event)
        response = self.agent.analyze(request, on_event=callback)
        if decision.disposition != RequestDisposition.QUALIFY:
            return response

        warning = (
            "Causal attribution is not supported by this observational retail "
            "dataset; reported promotion/campaign patterns are associations."
        )
        report = response.report.model_copy(
            update={"executive_summary": [warning, *response.report.executive_summary]}
        )
        qualification = RuntimeEvent(
            event_type="request_qualified",
            message=warning,
            progress=0.01,
            payload={"code": decision.code},
        )
        return response.model_copy(
            update={
                "report": report,
                "events": [qualification, *response.events],
            }
        )


def build_retail_domain_runtime(
    *,
    ontology_runtime: OntologyRuntime | None = None,
) -> RetailDomainRuntime:
    """Build the retail domain from environment-backed production configuration."""

    configured = os.getenv("EIW_RETAIL_DATA_DIR", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.append(Path("data/retail"))

    data = RetailDataEngine.demo()
    for path in candidates:
        if not path.exists():
            continue
        has_core_data = any(
            (path / name).exists()
            for name in (
                "transactions.parquet",
                "transaction_data.parquet",
                "transactions.csv",
                "transaction_data.csv",
            )
        )
        if has_core_data:
            data = RetailDataEngine.from_complete_journey(path)
            break

    supervisor_url = os.getenv("EIW_RETAIL_SUPERVISOR_URL", "").strip()
    supervisor = None
    if supervisor_url:
        supervisor = OpenAICompatibleSupervisor(
            base_url=supervisor_url,
            model=os.getenv("EIW_RETAIL_SUPERVISOR_MODEL", "qwen3"),
            api_key=os.getenv("EIW_RETAIL_SUPERVISOR_API_KEY", ""),
        )

    specialist_url = os.getenv("EIW_RETAIL_SPECIALIST_URL", "").strip()
    specialist = None
    if specialist_url:
        specialist = OpenAICompatibleSpecialistPolicy(
            base_url=specialist_url,
            model=os.getenv("EIW_RETAIL_SPECIALIST_MODEL", "qwen3"),
            api_key=os.getenv("EIW_RETAIL_SPECIALIST_API_KEY", ""),
        )

    return RetailDomainRuntime(
        RetailBARuntime(
            data,
            supervisor_policy=supervisor,
            specialist_policy=specialist,
            ontology_runtime=ontology_runtime,
        )
    )
