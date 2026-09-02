"""Small durable JSON store for the local reference application.

The domain contracts and PostgreSQL migration remain the production-shaped
boundary.  This file-backed adapter makes the complete product runnable with
one command when a local PostgreSQL instance is not available.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


class WorkspaceStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {"tasks": {}, "events": [], "evaluations": []}
        if self.path.exists() and self.path.stat().st_size:
            try:
                loaded = json.loads(self.path.read_text())
                if isinstance(loaded, dict):
                    self._data.update(loaded)
            except json.JSONDecodeError:
                self.path.rename(self.path.with_suffix(".corrupt.json"))

    def _save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._data, default=_json_default, indent=2))
        temporary.replace(self.path)

    def put_task(self, task: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            task["updated_at"] = datetime.now(UTC).isoformat()
            self._data["tasks"][task["task_id"]] = task
            self._save()
            return task

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._data["tasks"].get(task_id)
            return value if isinstance(value, dict) else None

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(self._data["tasks"].values(), key=lambda t: t.get("created_at", ""), reverse=True)

    def add_event(self, task_id: str, event_type: str, message: str, **payload: Any) -> dict[str, Any]:
        event = {
            "event_id": f"evt_{len(self._data['events']) + 1:06d}",
            "task_id": task_id,
            "event_type": event_type,
            "message": message,
            "occurred_at": datetime.now(UTC).isoformat(),
            **payload,
        }
        with self._lock:
            self._data["events"].append(event)
            task = self._data["tasks"].get(task_id)
            if task is not None:
                task.setdefault("events", []).append(event)
            self._save()
        return event

    def events(self, task_id: str) -> list[dict[str, Any]]:
        task = self.get_task(task_id)
        return list(task.get("events", [])) if task else []

    def add_evaluation(self, evaluation: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._data.setdefault("evaluations", []).append(evaluation)
            self._save()
        return evaluation

    def latest_evaluation(self) -> dict[str, Any] | None:
        with self._lock:
            items = self._data.get("evaluations", [])
            return items[-1] if items else None
