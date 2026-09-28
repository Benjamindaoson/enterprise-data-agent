"""Provider-neutral, instrumented chat clients for model-lane evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import perf_counter
from typing import Protocol
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class ModelPricing:
    input_per_million_usd: float = 0.0
    output_per_million_usd: float = 0.0


@dataclass(frozen=True)
class ChatResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: float


class UsageLedger:
    """Thread-safe usage accumulator shared by parallel specialist calls."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0
        self.latency_ms = 0.0

    def add(self, result: ChatResult) -> None:
        with self._lock:
            self.calls += 1
            self.prompt_tokens += result.prompt_tokens
            self.completion_tokens += result.completion_tokens
            self.cost_usd += result.cost_usd
            self.latency_ms += result.latency_ms

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            return {
                "calls": self.calls,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "cost_usd": round(self.cost_usd, 8),
                "model_latency_ms": round(self.latency_ms, 3),
            }


class PolicyTelemetry:
    """Counts bounded-decision failures and invalid allowlist selections."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.calls = 0
        self.failures = 0
        self.invalid_items = 0
        self.replan_calls = 0
        self.replan_nonempty = 0

    def record_call(self, *, stage: str | None = None) -> None:
        with self._lock:
            self.calls += 1
            if stage == "replan":
                self.replan_calls += 1

    def record_invalid(self, count: int) -> None:
        if count <= 0:
            return
        with self._lock:
            self.invalid_items += count

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1

    def record_replan_result(self, *, nonempty: bool) -> None:
        if not nonempty:
            return
        with self._lock:
            self.replan_nonempty += 1

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            return {
                "calls": self.calls,
                "failures": self.failures,
                "invalid_items": self.invalid_items,
                "invalid_decision_rate": (
                    self.invalid_items / self.calls if self.calls else 0.0
                ),
                "replan_calls": self.replan_calls,
                "replan_nonempty": self.replan_nonempty,
                "replan_rate": (
                    self.replan_nonempty / self.replan_calls
                    if self.replan_calls
                    else 0.0
                ),
            }


class ChatClient(Protocol):
    ledger: UsageLedger

    def complete(self, *, system: str, user: str) -> ChatResult: ...


def _cost(
    prompt_tokens: int,
    completion_tokens: int,
    pricing: ModelPricing,
) -> float:
    return (
        prompt_tokens * pricing.input_per_million_usd
        + completion_tokens * pricing.output_per_million_usd
    ) / 1_000_000.0


class OpenAICompatibleChatClient:
    """Chat Completions client used by OpenAI and Qwen compatible endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        pricing: ModelPricing | None = None,
        timeout_seconds: float = 60.0,
        ledger: UsageLedger | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.pricing = pricing or ModelPricing()
        self.timeout_seconds = timeout_seconds
        self.ledger = ledger or UsageLedger()

    def complete(self, *, system: str, user: str) -> ChatResult:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        started = perf_counter()
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.0,
                "stream": False,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        result = ChatResult(
            content=str(payload["choices"][0]["message"]["content"]),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=_cost(prompt_tokens, completion_tokens, self.pricing),
            latency_ms=(perf_counter() - started) * 1000.0,
        )
        self.ledger.add(result)
        return result


class AnthropicChatClient:
    """Minimal direct client for Anthropic Messages API."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        pricing: ModelPricing | None = None,
        timeout_seconds: float = 60.0,
        max_tokens: int = 512,
        ledger: UsageLedger | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.pricing = pricing or ModelPricing()
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.ledger = ledger or UsageLedger()

    def complete(self, *, system: str, user: str) -> ChatResult:
        started = perf_counter()
        response = httpx.post(
            f"{self.base_url}/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": 0.0,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        text_parts = [
            str(part.get("text", ""))
            for part in payload.get("content", [])
            if part.get("type") == "text"
        ]
        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("output_tokens") or 0)
        result = ChatResult(
            content="".join(text_parts),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=_cost(prompt_tokens, completion_tokens, self.pricing),
            latency_ms=(perf_counter() - started) * 1000.0,
        )
        self.ledger.add(result)
        return result


class GeminiChatClient:
    """Minimal direct client for Gemini generateContent API."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        pricing: ModelPricing | None = None,
        timeout_seconds: float = 60.0,
        max_output_tokens: int = 512,
        ledger: UsageLedger | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.pricing = pricing or ModelPricing()
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.ledger = ledger or UsageLedger()

    def complete(self, *, system: str, user: str) -> ChatResult:
        started = perf_counter()
        model = quote(self.model, safe="-._")
        response = httpx.post(
            f"{self.base_url}/models/{model}:generateContent",
            params={"key": self.api_key},
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": self.max_output_tokens,
                },
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            raise ValueError("Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        usage = payload.get("usageMetadata") or {}
        prompt_tokens = int(usage.get("promptTokenCount") or 0)
        completion_tokens = int(usage.get("candidatesTokenCount") or 0)
        result = ChatResult(
            content="".join(str(part.get("text", "")) for part in parts),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=_cost(prompt_tokens, completion_tokens, self.pricing),
            latency_ms=(perf_counter() - started) * 1000.0,
        )
        self.ledger.add(result)
        return result


def usage_snapshot(client: ChatClient) -> dict[str, int | float]:
    return client.ledger.snapshot()
