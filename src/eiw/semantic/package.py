"""Versioned semantic-package loader used by the Context Compiler."""

from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SemanticModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Availability(SemanticModel):
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")


class MetricDefinition(SemanticModel):
    id: str
    label: str
    expression: str
    unit: str
    availability: Availability
    description: str | None = None
    unavailable_behavior: str | None = None
    caution: str | None = None

    def covers(self, start: date | None, end: date | None) -> bool:
        return (
            start is not None
            and end is not None
            and self.availability.from_date <= start
            and end <= self.availability.to_date
        )


class DimensionDefinition(SemanticModel):
    id: str
    label: str
    source: str
    grain: str | None = None
    attributes: list[str] = Field(default_factory=list)


class PackageIdentity(SemanticModel):
    id: str
    version: str
    title: str
    timezone: str
    currency: str
    source_snapshot_alias: str
    default_snapshot: str
    description: str


class SemanticPackage(SemanticModel):
    package: PackageIdentity
    facts: list[dict[str, Any]]
    metrics: list[MetricDefinition]
    dimensions: list[DimensionDefinition]
    join_policies: list[dict[str, Any]]
    business_rules: list[dict[str, str]]
    quality_rules: list[dict[str, str]]
    access_policies: dict[str, dict[str, list[str]]]
    content_hash: str = ""

    @model_validator(mode="after")
    def identifiers_are_unique(self) -> "SemanticPackage":
        for name, values in (("metric", self.metrics), ("dimension", self.dimensions)):
            identifiers = [value.id for value in values]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{name} identifiers must be unique")
        return self

    def metric(self, metric_id: str) -> MetricDefinition:
        for metric in self.metrics:
            if metric.id == metric_id:
                return metric
        raise KeyError(f"unknown metric: {metric_id}")

    def dimension(self, dimension_id: str) -> DimensionDefinition:
        for dimension in self.dimensions:
            if dimension.id == dimension_id:
                return dimension
        raise KeyError(f"unknown dimension: {dimension_id}")


def load_semantic_package(path: Path) -> SemanticPackage:
    """Load a package and bind its exact source bytes as the content identity."""

    raw = path.read_bytes()
    parsed = yaml.safe_load(raw)
    package = SemanticPackage.model_validate(parsed)
    return package.model_copy(update={"content_hash": sha256(raw).hexdigest()})
