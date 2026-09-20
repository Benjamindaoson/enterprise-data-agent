from pathlib import Path

from eiw.business.models import BusinessScenario
from eiw.flywheel.evaluation import evaluate_policy
from eiw.flywheel.policies import ExpertPolicy
from eiw.flywheel.trajectory import TrajectoryStore, run_episode
from eiw.training.grpo import train_grpo
from eiw.training.policy import TransformerPolicy, load_policy
from eiw.training.sft import train_sft


def _build_sft_dataset(root: Path) -> Path:
    store = TrajectoryStore(root / "expert.jsonl")
    for scenario in BusinessScenario:
        for seed in range(3):
            store.append(run_episode(ExpertPolicy(), scenario=scenario, seed=seed))
    target = root / "sft.jsonl"
    assert store.export_sft(target) > 0
    return target


def test_sft_pipeline_trains_and_serializes_policy(tmp_path: Path):
    dataset = _build_sft_dataset(tmp_path)
    checkpoint = tmp_path / "sft.pt"
    metrics = train_sft(dataset, checkpoint, epochs=8, seed=5)
    assert checkpoint.exists()
    assert metrics["examples"] > 0
    assert 0.0 <= metrics["training_accuracy"] <= 1.0
    summary = evaluate_policy(TransformerPolicy(load_policy(checkpoint)), seeds=range(2))
    assert summary.episodes == 8


def test_grpo_pipeline_runs_from_sft_checkpoint(tmp_path: Path):
    dataset = _build_sft_dataset(tmp_path)
    sft_checkpoint = tmp_path / "sft.pt"
    grpo_checkpoint = tmp_path / "grpo.pt"
    train_sft(dataset, sft_checkpoint, epochs=5, seed=9)
    metrics = train_grpo(
        sft_checkpoint,
        grpo_checkpoint,
        iterations=1,
        group_size=2,
        seed=11,
    )
    assert grpo_checkpoint.exists()
    assert metrics["iterations"] == 1
    assert "final_mean_rollout_reward" in metrics
