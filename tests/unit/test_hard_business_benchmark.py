from eiw.benchmark.hard_env import HardBusinessEnvironment, generate_cases
from eiw.benchmark.policies import (
    DirectPolicy,
    HardExpertPolicy,
    HardRandomPolicy,
    PromptHeuristicPolicy,
)
from eiw.benchmark.runner import evaluate_hard_policy


def test_hard_environment_exercises_declared_failure_modes():
    cases = generate_cases(48)
    assert any(case.requires_memory for case in cases)
    assert any(case.tool_failure_step is not None for case in cases)
    assert any(case.evidence_mode.value == "CONFLICTING" for case in cases)
    assert any(case.alternate_path for case in cases)
    assert any(case.unsafe_write_available for case in cases)


def test_unapproved_write_is_blocked():
    case = next(case for case in generate_cases(16) if case.unsafe_write_available)
    env = HardBusinessEnvironment(case)
    result = env.step("execute_action")
    assert result.state.success is False
    assert result.state.policy_violations >= 1


def test_hard_benchmark_separates_reference_policies():
    cases = generate_cases(48)
    expert = evaluate_hard_policy(HardExpertPolicy(), cases)
    prompt = evaluate_hard_policy(PromptHeuristicPolicy(), cases)
    direct = evaluate_hard_policy(DirectPolicy(), cases)
    random = evaluate_hard_policy(HardRandomPolicy(3), cases)

    assert expert.success_rate > prompt.success_rate
    assert prompt.success_rate > direct.success_rate
    assert expert.average_reward > random.average_reward
    assert expert.policy_violation_rate == 0.0
