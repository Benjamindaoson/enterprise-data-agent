from __future__ import annotations

from eiw.retail.data import RetailDataEngine
from eiw.retail.models import WorkstreamName
from eiw.retail.skills import RetailAnalyticalWorkers
from eiw.retail.specialist_policy import (
    OpenAICompatibleSpecialistPolicy,
    SpecialistDecision,
)


class StoreContributionOnlyPolicy:
    def decide(
        self,
        *,
        workstream: WorkstreamName,
        question: str,
        allowed_skills: tuple[str, ...],
    ) -> SpecialistDecision:
        assert question
        if workstream == WorkstreamName.STORE:
            return SpecialistDecision(
                skills=["store_contribution", "not_allowed"],
                rationale="Start with contribution before deeper store diagnostics.",
            )
        return SpecialistDecision(
            skills=list(allowed_skills),
            rationale="Use the verified skill set.",
        )


class FailingSpecialistPolicy:
    def decide(self, **kwargs) -> SpecialistDecision:
        raise RuntimeError("specialist endpoint unavailable")


def test_model_specialist_selects_bounded_skill_subset() -> None:
    data = RetailDataEngine.demo()
    workers = RetailAnalyticalWorkers(
        data,
        policy=StoreContributionOnlyPolicy(),
    )
    result = workers.run(
        WorkstreamName.STORE,
        [7, 8],
        [5, 6],
        question="Which stores explain the sales movement?",
    )

    assert result.metadata["policy_source"] == "model"
    assert result.metadata["selected_skills"] == ["store_contribution"]
    anomaly = next(
        item for item in result.artifacts if item["type"] == "store_anomalies"
    )
    cross = next(
        item
        for item in result.artifacts
        if item["type"] == "store_commodity_scan"
    )
    assert anomaly["rows"] == []
    assert cross["rows"] == []
    assert result.rows


def test_specialist_model_failure_uses_full_deterministic_skill_set() -> None:
    data = RetailDataEngine.demo()
    workers = RetailAnalyticalWorkers(
        data,
        policy=FailingSpecialistPolicy(),
    )
    result = workers.run(
        WorkstreamName.PRODUCT,
        [7, 8],
        [5, 6],
        question="Decompose product movement.",
    )

    assert result.metadata["policy_source"] == "deterministic-fallback"
    assert set(result.metadata["selected_skills"]) == {
        "commodity_contribution",
        "price_volume",
    }
    assert result.rows
    decomposition = next(
        item
        for item in result.artifacts
        if item["type"] == "price_volume_decomposition"
    )
    assert decomposition["rows"]


def test_specialist_policy_json_parser_accepts_wrapped_object() -> None:
    parsed = OpenAICompatibleSpecialistPolicy._parse_json(
        'prefix {"skills":["store_contribution"],"rationale":"inspect"} suffix'
    )
    assert parsed["skills"] == ["store_contribution"]
