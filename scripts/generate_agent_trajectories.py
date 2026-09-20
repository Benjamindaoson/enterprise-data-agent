"""Generate expert and baseline trajectories for the post-training flywheel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.business.models import BusinessScenario
from eiw.flywheel.evaluation import evaluate_policy
from eiw.flywheel.policies import ExpertPolicy, RandomPolicy
from eiw.business.simulator import BusinessOperationsSimulator
from eiw.flywheel.trajectory import TrajectoryStore, run_episode
from eiw.workspace.data import IowaData


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/flywheel/expert-trajectories.jsonl"))
    parser.add_argument("--sft-output", type=Path, default=Path("artifacts/flywheel/sft-dataset.jsonl"))
    parser.add_argument("--episodes-per-scenario", type=int, default=20)
    args = parser.parse_args()

    if args.output.exists():
        args.output.unlink()
    store = TrajectoryStore(args.output)
    expert = ExpertPolicy()

    data = IowaData()
    public_simulator = BusinessOperationsSimulator.from_public_data(data, seed=0)
    public_signal = public_simulator.public_signal
    public_context = public_simulator.public_context
    data_source = "iowa-public-snapshot" if data.available() else "deterministic-fixture"
    for scenario in BusinessScenario:
        for seed in range(args.episodes_per_scenario):
            store.append(
                run_episode(
                    expert,
                    scenario=scenario,
                    seed=seed,
                    public_signal=public_signal,
                    public_context=public_context,
                )
            )

    sft_examples = store.export_sft(args.sft_output)
    payload = {
        "data_source": data_source,
        "public_context": public_context,
        "expert_eval": evaluate_policy(
            expert,
            seeds=range(5),
            public_signal=public_signal,
            public_context=public_context,
        ).as_dict(),
        "random_eval": evaluate_policy(
            RandomPolicy(17),
            seeds=range(5),
            public_signal=public_signal,
            public_context=public_context,
        ).as_dict(),
        "sft_examples": sft_examples,
        "failure_report": store.failure_report(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
