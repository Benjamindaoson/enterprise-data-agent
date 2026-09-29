"""Optional long-term memory backends for cross-task Agent learning."""

from __future__ import annotations

import importlib
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class LongTermMemoryItem:
    memory_id: str
    text: str
    memory_type: str = "memory"
    context: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def as_context(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "text": self.text,
            "type": self.memory_type,
            "context": self.context,
            "tags": list(self.tags),
        }


class LongTermMemoryBackend(Protocol):
    @property
    def name(self) -> str: ...

    def bank_id(self, scope: str) -> str: ...

    def recall(
        self,
        scope: str,
        query: str,
        *,
        tags: tuple[str, ...] = (),
    ) -> list[LongTermMemoryItem]: ...

    def retain(
        self,
        scope: str,
        content: str,
        *,
        context: str | None = None,
        metadata: dict[str, str] | None = None,
        tags: tuple[str, ...] = (),
    ) -> None: ...

    def reflect(self, scope: str, query: str) -> str: ...


@dataclass(slots=True)
class HindsightLongTermMemory:
    """Hindsight retain/recall/reflect adapter with normalized runtime contracts."""

    base_url: str
    api_key: str = field(default="", repr=False)
    bank_prefix: str = "eiw"
    max_tokens: int = 1200
    budget: str = "mid"
    timeout_seconds: float = 30.0
    client: Any | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.client is not None:
            return
        try:
            module = importlib.import_module("hindsight_client")
            client_cls = getattr(module, "Hindsight")
        except (ImportError, AttributeError) as exc:
            raise RuntimeError(
                "Hindsight is configured but hindsight-client is not installed; "
                "install the 'hindsight' optional dependency."
            ) from exc
        self.client = client_cls(
            base_url=self.base_url,
            api_key=self.api_key or None,
            timeout=self.timeout_seconds,
            user_agent="enterprise-data-agent/0.1",
        )

    @property
    def name(self) -> str:
        return "hindsight"

    def bank_id(self, scope: str) -> str:
        raw = f"{self.bank_prefix}-{scope}".lower()
        safe = re.sub(r"[^a-z0-9_.:-]+", "-", raw).strip("-")
        return safe[:128] or "eiw-default"

    def recall(
        self,
        scope: str,
        query: str,
        *,
        tags: tuple[str, ...] = (),
    ) -> list[LongTermMemoryItem]:
        assert self.client is not None
        kwargs: dict[str, Any] = {
            "bank_id": self.bank_id(scope),
            "query": query,
            "types": ["world", "experience", "observation"],
            "max_tokens": self.max_tokens,
            "budget": self.budget,
            "prefer_observations": True,
        }
        if tags:
            kwargs["tags"] = list(tags)
            kwargs["tags_match"] = "any_strict"
        response = self.client.recall(**kwargs)
        output: list[LongTermMemoryItem] = []
        for item in getattr(response, "results", []) or []:
            metadata = getattr(item, "metadata", None) or {}
            output.append(
                LongTermMemoryItem(
                    memory_id=str(getattr(item, "id", "")),
                    text=str(getattr(item, "text", "")).strip(),
                    memory_type=str(getattr(item, "type", "memory")),
                    context=(
                        str(getattr(item, "context"))
                        if getattr(item, "context", None) is not None
                        else None
                    ),
                    tags=tuple(
                        str(value) for value in (getattr(item, "tags", None) or [])
                    ),
                    metadata={
                        str(key): str(value)
                        for key, value in dict(metadata).items()
                    },
                )
            )
        return [item for item in output if item.text]

    def retain(
        self,
        scope: str,
        content: str,
        *,
        context: str | None = None,
        metadata: dict[str, str] | None = None,
        tags: tuple[str, ...] = (),
    ) -> None:
        assert self.client is not None
        self.client.retain(
            bank_id=self.bank_id(scope),
            content=content,
            context=context,
            metadata=metadata or {},
            tags=list(tags) or None,
        )

    def reflect(self, scope: str, query: str) -> str:
        assert self.client is not None
        response = self.client.reflect(
            bank_id=self.bank_id(scope),
            query=query,
            budget=self.budget,
         )
        return str(getattr(response, "text", "") or "").strip()


def long_term_memory_from_env() -> LongTermMemoryBackend | None:
    base_url = (
        os.getenv("EIW_HINDSIGHT_BASE_URL", "").strip()
        or os.getenv("HINDSIGHT_API_URL", "").strip()
    )
    backend = os.getenv("EIW_LONG_TERM_MEMORY_BACKEND", "").strip().lower()
    if not backend and base_url:
        backend = "hindsight"
    if not backend or backend in {"none", "disabled"}:
        return None
    if backend != "hindsight":
        raise ValueError(f"unsupported long-term memory backend: {backend}")
    return HindsightLongTermMemory(
        base_url=base_url or "http://127.0.0.1:8888",
        api_key=os.getenv("EIW_HINDSIGHT_API_KEY", "").strip(),
        bank_prefix=os.getenv("EIW_HINDSIGHT_BANK_PREFIX", "eiw").strip() or "eiw",
        max_tokens=max(128, int(os.getenv("EIW_HINDSIGHT_MAX_TOKENS", "1200"))),
        budget=os.getenv("EIW_HINDSIGHT_BUDGET", "mid").strip() or "mid",
        timeout_seconds=float(os.getenv("EIW_HINDSIGHT_TIMEOUT_SECONDS", "30")),
    )
