"""Provider boundary; production analysis remains independent of one vendor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class ModelProvider(Protocol):
    provider_id: str

    def structured(self, instruction: str, schema: Mapping[str, Any]) -> dict[str, Any]: ...


class DeterministicProvider:
    """Explicit offline provider used by the reference workflow and tests."""

    provider_id = "deterministic-reference-v1"

    def structured(self, instruction: str, schema: Mapping[str, Any]) -> dict[str, Any]:
        del instruction
        return {key: value for key, value in schema.items() if not isinstance(value, (list, dict))}
