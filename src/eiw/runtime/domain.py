"""Generic domain-runtime contract owned by BusinessAgentRuntime."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

DomainEventCallback = Callable[[Any], None]


class DomainRuntime(Protocol):
    """A bounded vertical implementation hosted by the canonical runtime."""

    domain_id: str

    def capabilities(self) -> dict[str, Any]:
        """Describe executable capabilities for this vertical."""
        ...

    def analyze(
        self,
        request: Any,
        *,
        on_event: DomainEventCallback | None = None,
    ) -> Any:
        """Execute one domain analysis request."""
        ...
