from scripts.check_hard_benchmark_acceptance import evaluate_acceptance


def test_hard_acceptance_requires_sft_and_grpo_improvements():
    result = {
        "direct": {"success_rate": 0.0},
        "random": {"success_rate": 0.0},
        "prompt": {"success_rate": 0.58},
        "sft": {
            "success_rate": 0.67,
            "average_reward": 0.59,
            "invalid_action_rate": 0.12,
            "policy_violation_rate": 0.08,
        },
        "sft_grpo": {
            "success_rate": 0.67,
            "average_reward": 0.64,
            "invalid_action_rate": 0.10,
            "policy_violation_rate": 0.08,
        },
    }
    acceptance = evaluate_acceptance(result)
    assert acceptance["passed"] is True

    result["sft_grpo"]["average_reward"] = 0.40
    acceptance = evaluate_acceptance(result)
    assert acceptance["passed"] is False
    assert acceptance["checks"]["grpo_improves_reward"] is False
