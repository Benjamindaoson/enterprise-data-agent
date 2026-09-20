from pathlib import Path

from eiw.benchmark.hard_env import generate_cases
from eiw.benchmark.training import evaluate_checkpoint, train_hard_grpo, train_hard_sft


def test_hard_sft_and_grpo_pipeline_runs(tmp_path: Path):
    cases = generate_cases(20)
    train_cases = cases[:16]
    held_out = cases[16:]
    sft = tmp_path / "sft.pt"
    grpo = tmp_path / "grpo.pt"

    sft_metrics = train_hard_sft(
        train_cases,
        sft,
        epochs=1,
        keep_fraction=0.5,
        seed=101,
    )
    assert sft.exists()
    assert sft_metrics["examples"] > 0
    sft_eval = evaluate_checkpoint(sft, held_out)
    assert sft_eval["cases"] == 4

    grpo_metrics = train_hard_grpo(
        sft,
        train_cases,
        grpo,
        iterations=1,
        group_size=2,
        seed=103,
    )
    assert grpo.exists()
    assert grpo_metrics["iterations"] == 1
    grpo_eval = evaluate_checkpoint(grpo, held_out)
    assert grpo_eval["cases"] == 4
