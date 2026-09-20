"""Checkpoint storage for durable agent state persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CheckpointStatus(str, Enum):
    """Status of a stored checkpoint."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class StoredCheckpoint:
    """A durable checkpoint of agent runtime state."""

    __slots__ = (
        "task_id",
        "version",
        "status",
        "state_json",
        "created_at",
        "updated_at",
    )

    def __init__(
        self,
        task_id: str,
        version: int,
        status: CheckpointStatus,
        state_json: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.task_id = task_id
        self.version = version
        self.status = CheckpointStatus(status) if not isinstance(status, CheckpointStatus) else status
        self.state_json = state_json
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def state(self) -> dict[str, Any]:
        """Parse and return the stored state dict."""
        if self.state_json:
            return json.loads(self.state_json)
        return {}

    def __repr__(self) -> str:
        return (
            f"StoredCheckpoint(task_id={self.task_id!r}, version={self.version}, "
            f"status={self.status.value!r})"
        )


class CheckpointStorage:
    """SQLite-backed durable checkpoint store for agent tasks."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            import os

            db_path = os.environ.get(
                "EIW_DATABASE_URL",
                "postgresql+psycopg://eiw:eiw@localhost:5432/eiw",
            )
            # Use a local SQLite file for the checkpoint store
            db_path = "checkpoints.db"
        self._db_path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None

    async def _get_conn(self) -> aiosqlite.Connection:
        """Lazily open and initialize the SQLite connection."""
        if self._conn is None:
            self._conn = await aiosqlite.connect(str(self._db_path))
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    task_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    state_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, version)
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON checkpoints(status)"
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_updated ON checkpoints(updated_at)"
            )
            await self._conn.commit()
        return self._conn

    async def save_checkpoint(
        self,
        task_id: str,
        version: int,
        status: CheckpointStatus,
        state: dict[str, Any],
    ) -> StoredCheckpoint:
        """Save or overwrite a checkpoint for the given task."""
        conn = await self._get_conn()
        now = datetime.utcnow().isoformat()
        state_json = json.dumps(state, default=str)
        await conn.execute(
            """
            INSERT INTO checkpoints (task_id, version, status, state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id, version) DO UPDATE SET
                status = excluded.status,
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (task_id, version, status.value, state_json, now, now),
        )
        await conn.commit()
        return StoredCheckpoint(
            task_id=task_id,
            version=version,
            status=status,
            state_json=state_json,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    async def get_checkpoint(
        self,
        task_id: str,
        version: int,
    ) -> StoredCheckpoint | None:
        """Retrieve a specific checkpoint version."""
        conn = await self._get_conn()
        cursor = await conn.execute(
            "SELECT * FROM checkpoints WHERE task_id = ? AND version = ?",
            (task_id, version),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return StoredCheckpoint(
            task_id=row["task_id"],
            version=row["version"],
            status=CheckpointStatus(row["status"]),
            state_json=row["state_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def get_latest_checkpoint(self, task_id: str) -> StoredCheckpoint | None:
        """Get the most recent checkpoint for a task."""
        conn = await self._get_conn()
        cursor = await conn.execute(
            "SELECT * FROM checkpoints WHERE task_id = ? ORDER BY version DESC LIMIT 1",
            (task_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return StoredCheckpoint(
            task_id=row["task_id"],
            version=row["version"],
            status=CheckpointStatus(row["status"]),
            state_json=row["state_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def get_active_tasks(self, limit: int = 100) -> list[StoredCheckpoint]:
        """List all active checkpoints, newest first."""
        conn = await self._get_conn()
        cursor = await conn.execute(
            "SELECT * FROM checkpoints WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
            (CheckpointStatus.ACTIVE.value, limit),
        )
        rows = await cursor.fetchall()
        return [
            StoredCheckpoint(
                task_id=row["task_id"],
                version=row["version"],
                status=CheckpointStatus(row["status"]),
                state_json=row["state_json"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    async def update_status(
        self,
        task_id: str,
        version: int,
        status: CheckpointStatus,
    ) -> None:
        """Update only the status of an existing checkpoint."""
        conn = await self._get_conn()
        now = datetime.utcnow().isoformat()
        await conn.execute(
            "UPDATE checkpoints SET status = ?, updated_at = ? WHERE task_id = ? AND version = ?",
            (status.value, now, task_id, version),
        )
        await conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None


# Module-level singleton (lazily initialized)
_storage: CheckpointStorage | None = None


def get_checkpoint_storage() -> CheckpointStorage:
    """Return the shared CheckpointStorage instance."""
    global _storage
    if _storage is None:
        _storage = CheckpointStorage()
    return _storage
