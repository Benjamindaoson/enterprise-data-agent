"""PostgreSQL-compatible durable trajectory, checkpoint and approval store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

trajectory_events = Table(
    "agent_trajectory_events",
    metadata,
    Column("event_id", String(64), primary_key=True),
    Column("trajectory_id", String(64), nullable=False, index=True),
    Column("task_id", String(64), nullable=False, index=True),
    Column("step_index", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

checkpoints = Table(
    "agent_checkpoints",
    metadata,
    Column("task_id", String(64), primary_key=True),
    Column("version", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

approvals = Table(
    "agent_approvals",
    metadata,
    Column("approval_id", String(64), primary_key=True),
    Column("task_id", String(64), nullable=False, index=True),
    Column("action_id", String(128), nullable=False),
    Column("status", String(32), nullable=False),
    Column("requested_by", String(128), nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("decided_by", String(128), nullable=True),
    Column("decided_at", DateTime(timezone=True), nullable=True),
    Column("reason", String(2000), nullable=True),
)


class ProductionStore:
    def __init__(self, database_url: str, *, create_schema: bool = True) -> None:
        self.engine: Engine = create_engine(database_url, future=True, pool_pre_ping=True)
        if create_schema:
            metadata.create_all(self.engine)

    def append_trajectory_event(
        self,
        *,
        trajectory_id: str,
        task_id: str,
        step_index: int,
        payload: dict[str, Any],
    ) -> str:
        event_id = uuid4().hex
        with self.engine.begin() as connection:
            connection.execute(
                insert(trajectory_events).values(
                    event_id=event_id,
                    trajectory_id=trajectory_id,
                    task_id=task_id,
                    step_index=step_index,
                    payload=payload,
                    created_at=datetime.now(UTC),
                )
            )
        return event_id

    def load_trajectory(self, trajectory_id: str) -> list[dict[str, Any]]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(trajectory_events)
                .where(trajectory_events.c.trajectory_id == trajectory_id)
                .order_by(trajectory_events.c.step_index, trajectory_events.c.created_at)
            ).mappings()
            return [dict(row) for row in rows]

    def save_checkpoint(
        self,
        *,
        task_id: str,
        version: int,
        payload: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(checkpoints.c.task_id).where(checkpoints.c.task_id == task_id)
            ).first()
            if existing:
                connection.execute(
                    update(checkpoints)
                    .where(checkpoints.c.task_id == task_id)
                    .values(version=version, payload=payload, updated_at=now)
                )
            else:
                connection.execute(
                    insert(checkpoints).values(
                        task_id=task_id,
                        version=version,
                        payload=payload,
                        updated_at=now,
                    )
                )

    def load_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(checkpoints).where(checkpoints.c.task_id == task_id)
            ).mappings().first()
            return dict(row) if row else None

    def request_approval(
        self,
        *,
        task_id: str,
        action_id: str,
        requested_by: str,
        reason: str | None = None,
    ) -> str:
        approval_id = uuid4().hex
        with self.engine.begin() as connection:
            connection.execute(
                insert(approvals).values(
                    approval_id=approval_id,
                    task_id=task_id,
                    action_id=action_id,
                    status="PENDING",
                    requested_by=requested_by,
                    requested_at=datetime.now(UTC),
                    reason=reason,
                )
            )
        return approval_id

    def decide_approval(
        self,
        approval_id: str,
        *,
        approved: bool,
        decided_by: str,
        reason: str | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            result = connection.execute(
                update(approvals)
                .where(approvals.c.approval_id == approval_id)
                .where(approvals.c.status == "PENDING")
                .values(
                    status="APPROVED" if approved else "REJECTED",
                    decided_by=decided_by,
                    decided_at=datetime.now(UTC),
                    reason=reason,
                )
            )
            if result.rowcount != 1:
                raise ValueError("approval not found or already decided")

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(approvals).where(approvals.c.approval_id == approval_id)
            ).mappings().first()
            return dict(row) if row else None

    def purge_task(self, task_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(trajectory_events).where(trajectory_events.c.task_id == task_id))
            connection.execute(delete(checkpoints).where(checkpoints.c.task_id == task_id))
            connection.execute(delete(approvals).where(approvals.c.task_id == task_id))
