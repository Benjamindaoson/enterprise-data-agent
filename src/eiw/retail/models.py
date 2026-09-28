"""Typed contracts for the retail Business Analysis Agent."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WorkstreamName(StrEnum):
    OVERVIEW = "overview"
    STORE = "store"
    PRODUCT = "product"
    PROMOTION = "promotion"
    CUSTOMER = "customer"


class RetailAnalysisRequest(BaseModel):
    question: str = Field(
        default="Analyze recent business performance, explain the main drivers, and recommend next actions.",
        min_length=3,
        max_length=5000,
    )
    current_weeks: list[int] = Field(default_factory=list)
    previous_weeks: list[int] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=3, le=20)
    max_workstreams: int = Field(default=5, ge=1, le=5)
    parent_task_id: str | None = Field(default=None, max_length=128)
    focus: dict[str, str] = Field(default_factory=dict)


class BusinessQuestionContext(BaseModel):
    metrics: list[str]
    dimensions: list[str]
    time_grain: str
    entities: dict[str, str] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    intents: list[str] = Field(default_factory=list)
    semantic_package_id: str
    semantic_package_version: str
    semantic_content_hash: str


class CodeAnalysisRequest(BaseModel):
    instruction: str = Field(min_length=3, max_length=5000)
    current_weeks: list[int] = Field(default_factory=list)
    previous_weeks: list[int] = Field(default_factory=list)
    max_rows: int = Field(default=100, ge=10, le=500)


class RuntimeEvent(BaseModel):
    event_type: str
    message: str
    elapsed_ms: float | None = Field(default=None, ge=0.0)
    workstream: str | None = None
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkstreamResult(BaseModel):
    name: WorkstreamName
    summary: str
    metrics: dict[str, float | int | str | None] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


class Insight(BaseModel):
    insight_id: str
    kind: str
    title: str
    finding: str
    driver: str
    business_impact: str
    recommended_action: str
    score: float = Field(ge=0.0, le=1.0)
    support: float = Field(ge=0.0, le=1.0)
    dimensions: dict[str, str] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ChartArtifact(BaseModel):
    chart_id: str
    title: str
    subtitle: str = ""
    chart_type: str
    option: dict[str, Any]
    insight_ids: list[str] = Field(default_factory=list)


class ChartRestyleRequest(BaseModel):
    chart: ChartArtifact
    instruction: str = Field(min_length=2, max_length=500)


class ActionCard(BaseModel):
    priority: str
    action: str
    target: str
    rationale: str
    monitor_kpi: str


class ExecutiveReport(BaseModel):
    title: str
    executive_summary: list[str]
    key_drivers: list[dict[str, Any]]
    opportunities: list[str]
    actions: list[ActionCard]
    monitoring: list[str]
    sections: list[dict[str, Any]] = Field(default_factory=list)


class RetailAnalysisResponse(BaseModel):
    task_id: str
    parent_task_id: str | None = None
    status: str
    dataset: dict[str, Any]
    question: str
    current_weeks: list[int]
    previous_weeks: list[int]
    semantics: BusinessQuestionContext
    kpis: dict[str, Any]
    workstreams: list[WorkstreamResult]
    insights: list[Insight]
    charts: list[ChartArtifact]
    report: ExecutiveReport
    events: list[RuntimeEvent]
    timings_ms: dict[str, float]
