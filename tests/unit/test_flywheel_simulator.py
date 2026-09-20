from pathlib import Path

from eiw.business.models import BusinessScenario
from eiw.business.simulator import EXPECTED_PATHS, BusinessOperationsSimulator
from eiw.flywheel.evaluation import evaluate_policy
from eiw.flywheel.policies import ExpertPolicy, RandomPolicy
from eiw.flywheel.trajectory import TrajectoryStore, run_episode


def test_expert_policy_completes_every_business_scenario():
    policy = ExpertPolicy()
    for scenario in BusinessScenario:
        trajectory = run_episode(policy, scenario=scenario, seed=1)
        assert trajectory.success is True
        assert trajectory.policy_violations == 0
        assert [step.action for step in trajectory.steps] == list(EXPECTED_PATHS[scenario])


def test_early_stop_is_a_policy_violation():
    simulator = BusinessOperationsSimulator(seed=2)
    simulator.reset(BusinessScenario.MARKETING_BUDGET)
    result = simulator.step("runtime.stop")
    assert result.done is True
    assert result.state.success is False
    assert result.state.policy_violations == 1
    assert result.reward < 0


def test_trajectory_store_exports_supervised_examples(tmp_path: Path):
    store = TrajectoryStore(tmp_path / "trajectories.jsonl")
    store.append(run_episode(ExpertPolicy(), scenario=BusinessScenario.ANALYTICS, seed=3))
    target = tmp_path / "sft.jsonl"
    count = store.export_sft(target)
    assert count == 4
    assert target.exists()
    assert store.failure_report()["failure_count"] == 0


def test_eval_separates_expert_from_random_policy():
    expert = evaluate_policy(ExpertPolicy(), seeds=range(3))
    random = evaluate_policy(RandomPolicy(4), seeds=range(3))
    assert expert.success_rate == 1.0
    assert expert.policy_violation_rate == 0.0
    assert expert.average_reward > random.average_reward
