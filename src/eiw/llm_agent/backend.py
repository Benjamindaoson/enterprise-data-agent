"""Open-weight Hugging Face causal-LM policy over discrete agent actions."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from eiw.benchmark.hard_env import HARD_ACTION_SPACE, HardState
from eiw.llm_agent.prompts import build_action_prompt


class LocalCausalLMActionPolicy:
    """Score complete action strings under a causal LM and choose the best one."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-0.6B",
        *,
        adapter_path: Path | None = None,
        prompted: bool = True,
        device_map: str | dict[str, Any] = "auto",
        torch_dtype: str = "auto",
    ) -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - optional heavy dependency
            raise RuntimeError("install the llm extra: pip install -e '.[llm]'") from exc

        self.torch = torch
        self.prompted = prompted
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map=device_map,
            torch_dtype=torch_dtype,
        )
        if adapter_path is not None:
            try:
                from peft import PeftModel
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("PEFT is required to load a LoRA adapter") from exc
            self.model = PeftModel.from_pretrained(self.model, str(adapter_path))
        self.model.eval()

    def _device(self) -> Any:
        return next(self.model.parameters()).device

    def action_log_probs(self, state_text: str) -> dict[str, float]:
        prompt = build_action_prompt(state_text, prompted=self.prompted)
        prompt_ids = self.tokenizer(prompt, add_special_tokens=True)["input_ids"]
        scores: dict[str, float] = {}
        device = self._device()

        with self.torch.no_grad():
            for action in HARD_ACTION_SPACE:
                action_ids = self.tokenizer(
                    " " + action,
                    add_special_tokens=False,
                )["input_ids"]
                ids = prompt_ids + action_ids
                input_ids = self.torch.tensor([ids], dtype=self.torch.long, device=device)
                logits = self.model(input_ids=input_ids).logits[0]
                log_probs = self.torch.log_softmax(logits, dim=-1)
                start = len(prompt_ids) - 1
                total = self.torch.tensor(0.0, device=device)
                for offset, token_id in enumerate(action_ids):
                    total = total + log_probs[start + offset, token_id]
                scores[action] = float(total.detach().cpu())
        return scores

    def choose_action(self, state: HardState) -> str:
        scores = self.action_log_probs(state.visible_text())
        return max(scores, key=scores.get)


class ActionScorePolicy:
    """Lightweight adapter used by tests and remote/model-server integrations."""

    def __init__(self, scorer: Any) -> None:
        self.scorer = scorer

    def choose_action(self, state: HardState) -> str:
        scores = self.scorer(state.visible_text(), HARD_ACTION_SPACE)
        if not scores:
            return "replan"
        return max(scores, key=scores.get)


def normalized_action_probabilities(scores: dict[str, float]) -> dict[str, float]:
    maximum = max(scores.values())
    exps = {key: math.exp(value - maximum) for key, value in scores.items()}
    denominator = sum(exps.values())
    return {key: value / denominator for key, value in exps.items()}
