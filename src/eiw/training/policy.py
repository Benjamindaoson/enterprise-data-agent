"""Tiny Transformer agent policy used for reproducible post-training experiments."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import Tensor, nn

from eiw.business.simulator import ACTION_SPACE, SimulatorState

ACTION_TO_ID = {name: index for index, name in enumerate(ACTION_SPACE)}
ID_TO_ACTION = {index: name for name, index in ACTION_TO_ID.items()}


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    vocab_size: int = 2048
    max_tokens: int = 48
    hidden_size: int = 64
    heads: int = 4
    layers: int = 2
    dropout: float = 0.0


def hashed_tokenize(text: str, config: PolicyConfig) -> list[int]:
    pieces = text.lower().replace("|", " ").replace("=", " ").split()
    ids = []
    for piece in pieces[: config.max_tokens]:
        digest = hashlib.sha256(piece.encode()).digest()
        ids.append(int.from_bytes(digest[:4], "big") % (config.vocab_size - 1) + 1)
    return ids or [1]


def collate_texts(texts: list[str], config: PolicyConfig) -> tuple[Tensor, Tensor]:
    encoded = [hashed_tokenize(text, config) for text in texts]
    length = min(config.max_tokens, max(len(item) for item in encoded))
    tokens = torch.zeros((len(encoded), length), dtype=torch.long)
    mask = torch.ones((len(encoded), length), dtype=torch.bool)
    for row, item in enumerate(encoded):
        item = item[:length]
        tokens[row, : len(item)] = torch.tensor(item, dtype=torch.long)
        mask[row, : len(item)] = False
    return tokens, mask


class TinyAgentTransformer(nn.Module):
    def __init__(self, config: PolicyConfig | None = None) -> None:
        super().__init__()
        self.config = config or PolicyConfig()
        self.embedding = nn.Embedding(self.config.vocab_size, self.config.hidden_size, padding_idx=0)
        layer = nn.TransformerEncoderLayer(
            d_model=self.config.hidden_size,
            nhead=self.config.heads,
            dim_feedforward=self.config.hidden_size * 4,
            dropout=self.config.dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=self.config.layers)
        self.head = nn.Linear(self.config.hidden_size, len(ACTION_SPACE))

    def forward(self, tokens: Tensor, padding_mask: Tensor) -> Tensor:
        hidden = self.encoder(self.embedding(tokens), src_key_padding_mask=padding_mask)
        keep = (~padding_mask).unsqueeze(-1)
        pooled = (hidden * keep).sum(dim=1) / keep.sum(dim=1).clamp(min=1)
        return self.head(pooled)

    def logits_for_texts(self, texts: list[str]) -> Tensor:
        tokens, mask = collate_texts(texts, self.config)
        return self(tokens, mask)


class TransformerPolicy:
    def __init__(self, model: TinyAgentTransformer) -> None:
        self.model = model

    def choose_action(self, state: SimulatorState) -> str:
        self.model.eval()
        with torch.no_grad():
            logits = self.model.logits_for_texts([state.as_policy_text()])
            action_id = int(logits.argmax(dim=-1).item())
        return ID_TO_ACTION[action_id]


def save_policy(model: TinyAgentTransformer, path: Path, metadata: dict[str, object] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "config": vars(model.config),
            "metadata": metadata or {},
        },
        path,
    )


def load_policy(path: Path) -> TinyAgentTransformer:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = TinyAgentTransformer(PolicyConfig(**payload["config"]))
    model.load_state_dict(payload["state_dict"])
    return model
