"""Agent Lightning local-runner entrypoint for the real Retail BA Agent Harness."""

from __future__ import annotations

import json
import os

from eiw.retail.agent_lightning import (
    RetailAgentLightningCase,
    reward_retail_response,
)
from eiw.retail.domain import build_retail_domain_runtime
from eiw.retail.models import RetailAnalysisRequest
from eiw.training.agent_lightning import AgentLightningConfig


def load_case_from_env() -> RetailAgentLightningCase:
    raw = os.environ.get("EIW_AGL_CASE_JSON", "").strip()
    if not raw:
        raise RuntimeError("EIW_AGL_CASE_JSON is required for Agent Lightning local rollout")
    return RetailAgentLightningCase.model_validate_json(raw)


def execute_retail_rollout() -> dict[str, object]:
    """Run the unchanged Retail Harness and publish verifier events to Agent Lightning."""

    config = AgentLightningConfig.from_env()
    if config is None:
        raise RuntimeError("Agent Lightning rollout environment is not configured")
    case = load_case_from_env()
    domain = build_retail_domain_runtime()
    response = domain.analyze(
        RetailAnalysisRequest(
            question=case.question,
            current_weeks=case.current_weeks,
            previous_weeks=case.previous_weeks,
            tenant_id="agent-lightning",
            user_id=case.case_id,
        )
    )
    reward, metrics = reward_retail_response(response, case)
    if config.event_url:
        config.post_event(
            "eiw_metrics",
            {
                "case_id": case.case_id,
                "task_id": response.task_id,
                **metrics,
            },
        )
        config.post_reward(
            reward,
            source="eiw-retail-verifier",
            reason=f"case={case.case_id}",
        )
    return {
        "case_id": case.case_id,
        "task_id": response.task_id,
        "reward": reward,
        "metrics": metrics,
    }


class RetailAgentLightningRunner:
    """Agent class imported by Agent Lightning local rollout controller."""

    async def run(self) -> None:
        result = execute_retail_rollout()
        print(json.dumps(result, ensure_ascii=False))
