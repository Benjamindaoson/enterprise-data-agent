"""Supervised post-training for next-skill/action selection."""

from __future__ import annotations

import json
import random
from pathlib import Path

import torch
from torch import nn

from eiw.training.policy import (
    ACTION_TO_ID,
    PolicyConfig,
    TinyAgentTransformer,
    collate_texts,
    save_policy,
)


def load_sft_examples(path: Path) -> list[tuple[str, int]]:
    examples: list[tuple[str, int]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        examples.append((item["input"], ACTION_TO_ID[item["target"]]))
    if not examples:
        raise ValueError("SFT dataset is empty")
    return examples


def train_sft(
    dataset_path: Path,
    output_path: Path,
    *,
    epochs: int = 30,
    learning_rate: float = 3e-3,
    seed: int = 7,
    config: PolicyConfig | None = None,
) -> dict[str, float | int]:
    torch.manual_seed(seed)
    random.seed(seed)
    examples = load_sft_examples(dataset_path)
    random.shuffle(examples)
    model = TinyAgentTransformer(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    loss_fn = nn.CrossEntropyLoss()

    losses: list[float] = []
    for _ in range(epochs):
        random.shuffle(examples)
        texts = [item[0] for item in examples]
        labels = torch.tensor([item[1] for item in examples], dtype=torch.long)
        tokens, mask = collate_texts(texts, model.config)
        logits = model(tokens, mask)
        loss = loss_fn(logits, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))

    model.eval()
    texts = [item[0] for item in examples]
    labels = torch.tensor([item[1] for item in examples], dtype=torch.long)
    with torch.no_grad():
        tokens, mask = collate_texts(texts, model.config)
        accuracy = float((model(tokens, mask).argmax(dim=-1) == labels).float().mean())
    metrics: dict[str, float | int] = {
        "examples": len(examples),
        "epochs": epochs,
        "final_loss": losses[-1],
        "training_accuracy": accuracy,
    }
    save_policy(model, output_path, metadata={"stage": "sft", **metrics})
    return metrics
