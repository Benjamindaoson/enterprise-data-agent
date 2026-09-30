#!/usr/bin/env python3
"""Train the real Retail BA Agent Harness with Agent Lightning v1.0 + VERL."""

from __future__ import annotations

import argparse
import importlib.resources
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise ValueError(f"Agent Lightning dataset is empty: {path}")
    return rows


def build_config(
    *,
    model: str,
    agl_base_url: str,
    agl_key: str,
    run_name: str,
    config_overrides: Sequence[str] = (),
) -> Any:
    """Build Agent Lightning official VERL config for the Retail Harness."""

    try:
        from hydra import compose, initialize_config_dir
        from omegaconf import OmegaConf
    except ImportError as exc:
        raise RuntimeError(
            "Install the agent-lightning optional dependencies before building the training config."
        ) from exc

    try:
        config_dir = str(importlib.resources.files("agentlightning.verl"))
        with initialize_config_dir(config_dir=config_dir, version_base=None):
            base_cfg = compose(config_name="config")
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "Agent Lightning VERL support is not installed. Follow the upstream v1.0 VERL setup before GPU training."
        ) from exc

    overrides = {
        "algorithm": {"adv_estimator": "grpo", "use_kl_in_reward": False},
        "data": {
            "train_batch_size": 8,
            "max_prompt_length": 4096,
            "max_response_length": 2048,
        },
        "actor_rollout_ref": {
            "rollout": {
                "tensor_model_parallel_size": 1,
                "n": 4,
                "log_prob_micro_batch_size_per_gpu": 1,
                "multi_turn": {"format": "hermes"},
                "name": "vllm",
                "gpu_memory_utilization": 0.72,
            },
            "actor": {
                "ppo_mini_batch_size": 8,
                "ppo_micro_batch_size_per_gpu": 1,
                "optim": {"lr": 1e-6},
                "use_kl_loss": False,
                "kl_loss_coef": 0.0,
                "entropy_coeff": 0,
                "clip_ratio_low": 0.2,
                "clip_ratio_high": 0.28,
            },
            "ref": {"log_prob_micro_batch_size_per_gpu": 1},
            "model": {
                "path": model,
                "use_remove_padding": True,
                "enable_gradient_checkpointing": True,
            },
        },
        "trainer": {
            "n_gpus_per_node": 1,
            "val_before_train": True,
            "critic_warmup": 0,
            "logger": ["console"],
            "project_name": "enterprise-data-agent",
            "experiment_name": run_name,
            "nnodes": 1,
            "save_freq": 10,
            "test_freq": 5,
            "total_epochs": 2,
        },
        "agentlightning": {
            "agl_base_url": agl_base_url,
            "agl_key": agl_key,
            "rollout_timeout_seconds": 600,
            "trace_aggregator": {
                "level": "trajectory",
                "trajectory_max_prompt_length": 4096,
                "trajectory_max_response_length": 2048,
            },
            "async_rollout": {"enabled": False, "async_train_batch_size": 32},
            "local": {
                "agent_class": "eiw.training.agent_lightning_agent:RetailAgentLightningRunner",
                "env_map": {"EIW_AGL_CASE_JSON": "input"},
            },
        },
    }

    OmegaConf.set_struct(base_cfg, False)
    return OmegaConf.merge(
        base_cfg,
        OmegaConf.create(overrides),
        OmegaConf.from_dotlist(list(config_overrides)),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--train-file",
        type=Path,
        default=Path("artifacts/agent-lightning/retail-cases.jsonl"),
    )
    parser.add_argument(
        "--val-file",
        type=Path,
        default=Path("artifacts/agent-lightning/retail-cases.jsonl"),
    )
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--agl-base-url", default="http://127.0.0.1:8181")
    parser.add_argument("--agl-key", default="eiw-dev-key")
    parser.add_argument("--run-name", default="retail-ba-agent")
    parser.add_argument("--config-only", action="store_true")
    args, config_overrides = parser.parse_known_args()

    config = build_config(
        model=args.model,
        agl_base_url=args.agl_base_url,
        agl_key=args.agl_key,
        run_name=args.run_name,
        config_overrides=config_overrides,
    )

    if args.config_only:
        from omegaconf import OmegaConf

        print(OmegaConf.to_yaml(config, resolve=True))
        return 0

    train_dataset = load_jsonl(args.train_file)
    val_dataset = load_jsonl(args.val_file)

    try:
        from agentlightning.verl.entrypoint import run_ppo
    except ImportError as exc:
        raise RuntimeError(
            "Full Agent Lightning training requires its VERL stack. Run upstream Agent Lightning v1.0 VERL setup first."
        ) from exc

    print(f"Train cases: {len(train_dataset)}")
    print(f"Validation cases: {len(val_dataset)}")
    run_ppo(config, train_dataset=train_dataset, val_dataset=val_dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
