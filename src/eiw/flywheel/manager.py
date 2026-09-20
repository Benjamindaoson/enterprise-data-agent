"""End-to-end trajectory -> evaluation -> dataset flywheel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eiw.business.models import BusinessScenario
from eiw.flywheel.evaluation import evaluate_policy
from eiw.flywheel.policies import ExpertPolicy, RandomPolicy
from eiw.flywheel.trajectory import AgentPolicy, TrajectoryStore, run_episode


class FlywheelManager:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.trajectory_path = root / "trajectories.jsonl"
        self.sft_path = root / "sft-dataset.jsonl"
        self.report_path = root / "flywheel-report.json"

    def collect(
        self,
        policy: AgentPolicy,
        *,
        episodes_per_scenario: int = 10,
        append: bool = False,
    ) -> TrajectoryStore:
        if self.trajectory_path.exists() and not append:
            self.trajectory_path.unlink()
        store = TrajectoryStore(self.trajectory_path)
        for scenario in BusinessScenario:
            for seed in range(episodes_per_scenario):
                store.append(run_episode(policy, scenario=scenario, seed=seed))
        return store

    def build_report(self, policy: AgentPolicy) -> dict[str, Any]:
        store = TrajectoryStore(self.trajectory_path)
        examples = store.export_sft(self.sft_path)
        report = {
            "policy_eval": evaluate_policy(policy, seeds=range(10)).as_dict(),
            "expert_reference": evaluate_policy(ExpertPolicy(), seeds=range(5)).as_dict(),
            "random_reference": evaluate_policy(RandomPolicy(29), seeds=range(5)).as_dict(),
            "failure_report": store.failure_report(),
            "sft_examples": examples,
        }
        self.report_path.write_text(json.dumps(report, indent=2))
        return report
