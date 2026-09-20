"""Layered memory contracts for long-horizon business-agent tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MemoryKind(StrEnum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"


@dataclass(slots=True)
class MemoryRecord:
    key: str
    kind: MemoryKind
    value: Any
    task_id: str | None = None
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    def expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return self.expires_at is not None and self.expires_at <= current


@dataclass(slots=True)
class MemoryStore:
    _records: dict[tuple[MemoryKind, str], MemoryRecord] = field(default_factory=dict)

    def put(self, record: MemoryRecord) -> MemoryRecord:
        identity = (record.kind, record.key)
        existing = self._records.get(identity)
        if existing is not None:
            record.version = existing.version + 1
        self._records[identity] = record
        return record

    def get(self, kind: MemoryKind, key: str) -> MemoryRecord | None:
        record = self._records.get((kind, key))
        if record is None:
            return None
        if record.expired():
            del self._records[(kind, key)]
            return None
        return record

    def query(
        self,
        *,
        kind: MemoryKind | None = None,
        task_id: str | None = None,
    ) -> list[MemoryRecord]:
        output: list[MemoryRecord] = []
        for record in list(self._records.values()):
            if record.expired():
                self._records.pop((record.kind, record.key), None)
                continue
            if kind is not None and record.kind != kind:
                continue
            if task_id is not None and record.task_id != task_id:
                continue
            output.append(record)
        return sorted(output, key=lambda item: item.created_at)
