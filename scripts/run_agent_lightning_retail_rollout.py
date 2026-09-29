#!/usr/bin/env python3
"""Run one Retail BA Agent rollout under an Agent Lightning controller."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from eiw.retail.agent_lightning import (
    RetailAgentLightningCase,
    reward_retail_response,
)
from eiw.retail.domain import build_retail_domain_runtime
from eiw.retail.models import RetailAnalysisRequest
from eiw.training.agent_lightning import AgentLightningConfig


def _load_case(path: Path | None) -> RetailAgentLightningCase:
    raw = os.getenv("EIW_AGL_CASE_JSON", "").strip()
    if raw:
        return RetailAgentLightningCase.model_validate_json(raw)
    if path is None:
        raise RuntimeError("EIW_AGL_CASE_JSON or --case-json is required")
    return RetailAgentLightningCase.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-json", type=Path)
    args = parser.parse_args()

    config = AgentLightningConfig.from_env()
    if config is None:
        raise RuntimeError(
            "AGL_OPENAI_BASE_URL is required for Agent Lightning rollout mode"
        )
    case = _load_case(args.case_json)

    domain = build_retail_domain_runtime()
    response = domain.analyze(
        RetailAnalysisRequest(
            question=case.question,
            current_weeks=case.current_weeks,
            previous_weeks=case.previous_weeks,
        )
    )
    reward, metrics = reward_retail_response(response, case)
    if config.event_url:
        config.post_event(
            "eiw_metrics",
            {
                "case_id": case.case_id,
                **metrics,
                "task_id": response.task_id,
            },
        )
        config.post_reward(
            reward,
            source="eiw-retail-verifier",
            reason=f"case={case.case_id}",
        )

    print(
        json.dumps(
            {
                "case_id": case.case_id,
                "task_id": response.task_id,
                "reward": round(reward, 6),
                "metrics": metrics,
                "model_proxy": config.openai_base_url,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
