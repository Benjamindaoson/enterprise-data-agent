"""Domain runtime contracts for the canonical BusinessAgentRuntime."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


DomainEventCallback = Callable[[object], None]


class DomainRuntime(Protocol):
    """A domain adapter hosted by the single application-level runtime."""

    domain_id: str

    def capabilities(self) -> dict[str, Any]: ...

    def analyze(
        self,
        request: object,
        *,
        on_event: DomainEventCallback | None = None,
    ) -> object: ...


class DomainRuntimeError(RuntimeError):
    """Typed domain failure that API layers can map without parsing messages."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "DOMAIN_RUNTIME_ERROR",
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class DomainRequestRejected(DomainRuntimeError):
    def __init__(self, message: str, *, code: str = "REQUEST_REJECTED") -> None:
        super().__init__(message, code=code, status_code=422)


class DomainClarificationRequired(DomainRuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "CLARIFICATION_REQUIRED",
    ) -> None:
        super().__init__(message, code=code, status_code=409)
