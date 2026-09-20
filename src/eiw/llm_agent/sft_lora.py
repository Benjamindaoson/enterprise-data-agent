"""LoRA supervised fine-tuning for real causal-LM business-agent policies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_rows(path: Path) -> list[dict[str, str]]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError("LLM SFT dataset is empty")
    return rows


def train_lora_sft(
    dataset_path: Path,
    output_dir: Path,
    *,
    model_name: str = "Qwen/Qwen3-0.6B",
    epochs: int = 1,
    learning_rate: float = 2e-4,
    max_length: int = 512,
    seed: int = 17,
) -> dict[str, Any]:
    try:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install the llm extra: pip install -e '.[llm]'") from exc

    torch.manual_seed(seed)
    rows = _load_rows(dataset_path)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto",
    )
    lora = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.train()
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=learning_rate,
    )
    device = next(model.parameters()).device
    losses: list[float] = []

    for _ in range(epochs):
        for row in rows:
            prompt_ids = tokenizer(
                row["prompt"],
                add_special_tokens=True,
                truncation=True,
                max_length=max_length - 32,
            )["input_ids"]
            target_ids = tokenizer(
                " " + row["target"] + (tokenizer.eos_token or ""),
                add_special_tokens=False,
                truncation=True,
                max_length=32,
            )["input_ids"]
            ids = (prompt_ids + target_ids)[-max_length:]
            prompt_kept = max(0, len(ids) - len(target_ids))
            labels = [-100] * prompt_kept + target_ids[-(len(ids) - prompt_kept):]
            input_ids = torch.tensor([ids], dtype=torch.long, device=device)
            label_tensor = torch.tensor([labels], dtype=torch.long, device=device)
            result = model(input_ids=input_ids, labels=label_tensor)
            optimizer.zero_grad()
            result.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(result.loss.detach().cpu()))

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    metrics = {
        "model_name": model_name,
        "examples": len(rows),
        "epochs": epochs,
        "final_loss": losses[-1],
        "mean_loss": sum(losses) / len(losses),
        "trainable_parameters": sum(
            parameter.numel() for parameter in model.parameters() if parameter.requires_grad
        ),
    }
    (output_dir / "training-metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics
