from pathlib import Path

from eiw.benchmark.hard_env import generate_cases
from eiw.benchmark.runner import evaluate_hard_policy
from eiw.llm_agent.backend import ActionScorePolicy
from eiw.llm_agent.dataset import export_llm_sft_dataset
from eiw.llm_agent.prompts import build_action_prompt


def test_prompt_contains_governance_and_action_contract():
    prompt = build_action_prompt("scenario=MARKETING_BUDGET memory_required=1")
    assert "approval" in prompt.lower()
    assert "retrieve_memory" in prompt
    assert "execute_action" in prompt


def test_llm_sft_dataset_has_train_eval_split(tmp_path: Path):
    stats = export_llm_sft_dataset(tmp_path / "train.jsonl", cases=16)
    assert stats["train_cases"] == 12
    assert stats["eval_cases"] == 4
    assert stats["train_examples"] > stats["train_cases"]
    assert (tmp_path / "train-eval.jsonl").exists()


def test_action_score_backend_can_drive_held_out_environment():
    def scorer(state: str, actions: tuple[str, ...]) -> dict[str, float]:
        scores = {action: -10.0 for action in actions}
        if "failed=1" in state and "recovered=0" in state:
            scores["retry_tool"] = 10.0
        elif "metric=0" in state:
            scores["inspect_metric"] = 10.0
        elif "memory_required=1" in state and "memory=0" in state:
            scores["retrieve_memory"] = 10.0
        elif "evidence=CONFLICTING" in state and "checked=0" in state:
            scores["cross_check"] = 10.0
        elif "segment=0" in state:
            scores["inspect_segment"] = 10.0
        elif "proposal=0" in state:
            scores["build_proposal"] = 10.0
        elif "scenario=ANALYTICS" in state:
            scores["stop"] = 10.0
        elif "approved=0" in state:
            scores["request_approval"] = 10.0
        else:
            scores["execute_action"] = 10.0
        return scores

    result = evaluate_hard_policy(ActionScorePolicy(scorer), generate_cases(12))
    assert result.success_rate > 0.5
