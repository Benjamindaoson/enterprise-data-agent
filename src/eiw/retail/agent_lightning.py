"""Retail outcome verifier used by Agent Lightning rollouts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from eiw.retail.models import RetailAnalysisResponse
from eiw.training.agent_lightning import compose_reward


class RetailAgentLightningCase(BaseModel):
    case_id: str = "adhoc"
    question: str
    current_weeks: list[int] = Field(default_factory=list)
    previous_weeks: list[int] = Field(default_factory=list)
    expected_driver_terms: list[str] = Field(default_factory=list)
    expected_metrics: list[str] = Field(default_factory=list)
    expected_dimensions: list[str] = Field(default_factory=list)
    expected_intents: list[str] = Field(default_factory=list)


def _coverage(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0
    actual_lower = {item.lower() for item in actual}
    matched = sum(1 for item in expected if item.lower() in actual_lower)
    return matched / len(expected)


def score_retail_response(
    response: RetailAnalysisResponse,
    case: RetailAgentLightningCase,
) -> dict[str, float]:
    semantic_parts = [
        _coverage(case.expected_metrics, list(response.semantics.metrics)),
        _coverage(case.expected_dimensions, list(response.semantics.dimensions)),
        _coverage(case.expected_intents, list(response.semantics.intents)),
    ]
    semantic_coverage = sum(semantic_parts) / len(semantic_parts)

    corpus = " ".join(
        [
            *[
                f"{item.title} {item.finding} {item.driver}"
                for item in response.insights
            ],
            *response.report.executive_summary,
        ]
    ).lower()
    if case.expected_driver_terms:
        driver_recall = sum(
            1 for term in case.expected_driver_terms if term.lower() in corpus
        ) / len(case.expected_driver_terms)
    else:
        driver_recall = 1.0

    return {
        "semantic_coverage": semantic_coverage,
        "driver_recall": driver_recall,
        "action_coverage": 1.0 if response.report.actions else 0.0,
        "task_completion": 1.0 if response.status == "COMPLETED" else 0.0,
    }


def reward_retail_response(
    response: RetailAnalysisResponse,
    case: RetailAgentLightningCase,
) -> tuple[float, dict[str, float]]:
    metrics = score_retail_response(response, case)
    reward = compose_reward(
        metrics,
        weights={
            "semantic_coverage": 0.35,
            "driver_recall": 0.35,
            "action_coverage": 0.15,
            "task_completion": 0.15,
        },
    )
    return reward, metrics
