"""Semantic Layer v2 - Enhanced metric and dimension definitions.

This module provides typed definitions for metrics and dimensions that form the
authoritative semantic contract. No metric formula may be created by the model;
all authoritative definitions must come from validated semantic packages.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SemanticModel(BaseModel):
    """Base model with strict validation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DataClassification(str, Enum):
    """Data classification levels."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class TimeGrain(str, Enum):
    """Valid time grains for metrics."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    ALL = "ALL"


class AggregationType(str, Enum):
    """Aggregation types for metrics."""

    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    COUNT_DISTINCT = "COUNT_DISTINCT"
    MIN = "MIN"
    MAX = "MAX"
    MEDIAN = "MEDIAN"
    STDDEV = "STDDEV"


class SemanticType(str, Enum):
    """Semantic types for metrics and dimensions."""

    CURRENCY = "CURRENCY"
    QUANTITY = "QUANTITY"
    RATIO = "RATIO"
    PERCENTAGE = "PERCENTAGE"
    RATE = "RATE"
    COUNT = "COUNT"
    DURATION = "DURATION"
    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
    BOOLEAN = "BOOLEAN"
    TEXT = "TEXT"


# =============================================================================
# Availability and freshness
# =============================================================================


class Availability(SemanticModel):
    """Metric/dimension availability window."""

    from_date: date = Field(alias="from", description="Available from date")
    to_date: date = Field(alias="to", description="Available to date (exclusive)")
    status: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE", "DEPRECATED"] = "AVAILABLE"
    note: str | None = Field(default=None, description="Reason for partial/unavailable")

    @field_validator("to_date")
    @classmethod
    def to_after_from(cls, v: date, info: Any) -> date:
        from_date = info.data.get("from_date")
        if from_date and v <= from_date:
            raise ValueError("to_date must be after from_date")
        return v

    def covers(self, start: date | None, end: date | None) -> bool:
        """Check if availability covers the given date range."""
        if start is None or end is None:
            return True
        return self.from_date <= start and end <= self.to_date

    def model_dump(self, **kwargs):
        """Override dump to use 'from' and 'to' keys for YAML compatibility."""
        data = super().model_dump(**kwargs)
        # Convert from_date/to_date to from/to for YAML output
        if "from_date" in data:
            data["from"] = data.pop("from_date")
        if "to_date" in data:
            data["to"] = data.pop("to_date")
        return data


class Freshness(SemanticModel):
    """Data freshness information."""

    typical_delay_hours: int = Field(
        ge=0,
        description="Typical delay in hours from business date to data availability",
    )
    max_delay_hours: int = Field(
        ge=0,
        description="Maximum delay in hours",
    )
    update_frequency: Literal["realtime", "hourly", "daily", "weekly"] = "daily"
    last_updated_at: date | None = None


# =============================================================================
# Dimension definitions
# =============================================================================


class DimensionHierarchy(SemanticModel):
    """Dimension hierarchy for drill-down."""

    level: int = Field(ge=1, description="Hierarchy level (1 = finest grain)")
    name: str = Field(description="Level name")
    parent_level: int | None = Field(default=None, description="Parent level")


def _default_availability() -> dict:
    """Default availability spanning all time as dict (for Pydantic factory)."""
    return {"from": "1900-01-01", "to": "2100-12-31"}


class DimensionDefinition(SemanticModel):
    """Enhanced dimension definition."""

    id: str = Field(min_length=1, max_length=100, description="Unique dimension ID")
    name: str = Field(min_length=1, max_length=200, description="Display name")
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names for resolution",
    )
    description: str = Field(default="", description="Business description")

    # Physical mapping
    source_table: str = Field(description="Source table name")
    source_column: str = Field(description="Source column name")
    source_schema: str | None = Field(default=None, description="Source schema")

    # Grain and hierarchy
    grain: TimeGrain | None = Field(default=None, description="Dimension grain")
    hierarchy: list[DimensionHierarchy] = Field(
        default_factory=list,
        description="Drill-down hierarchy levels",
    )

    # Join rules
    join_paths: list[str] = Field(
        default_factory=list,
        description="Valid join paths from this dimension",
    )
    cardinality: Literal["low", "medium", "high"] = "medium"
    cardinality_estimate: int | None = Field(
        default=None,
        ge=0,
        description="Estimated cardinality",
    )

    # Policy tags
    policy_tags: list[str] = Field(
        default_factory=list,
        description="Policy tags for access control",
    )
    classification: DataClassification = DataClassification.INTERNAL

    # Availability
    availability: Availability = Field(
        default_factory=_default_availability,
    )

    # Metadata
    owner: str | None = Field(default=None, description="Business owner")
    documentation_url: str | None = None


# =============================================================================
# Metric definitions
# =============================================================================


class MetricFormula(SemanticModel):
    """Metric computation formula (authoritative source only)."""

    type: Literal["column", "expression", "aggregation", "derived"]
    expression: str = Field(description="SQL expression or column reference")
    source_table: str | None = Field(default=None, description="Primary source table")
    source_columns: list[str] = Field(default_factory=list, description="Source columns")
    required_dimensions: list[str] = Field(
        default_factory=list,
        description="Dimensions required for computation",
    )

    # For derived metrics
    base_metrics: list[str] = Field(
        default_factory=list,
        description="Base metrics for derived calculations",
    )
    derivation_formula: str | None = Field(
        default=None,
        description="Formula for derived metrics",
    )


class MetricJoinPath(SemanticModel):
    """Valid join path for a metric."""

    path_id: str = Field(description="Unique path identifier")
    intermediate_tables: list[str] = Field(
        description="Intermediate tables in join path",
    )
    join_conditions: list[str] = Field(
        description="Join conditions as SQL expressions",
    )
    estimated_rows: int | None = Field(
        default=None,
        ge=0,
        description="Estimated result row count",
    )


class MetricSupportedGrain(SemanticModel):
    """Supported time grain for a metric."""

    grain: TimeGrain
    available: bool = True
    note: str | None = None


class MetricBusinessRule(SemanticModel):
    """Business rule associated with a metric."""

    rule_id: str
    description: str
    expression: str
    severity: Literal["error", "warning", "info"] = "warning"


class MetricLineageReference(SemanticModel):
    """Lineage reference for metric tracing."""

    reference_type: Literal["upstream", "downstream", "related"]
    entity_type: Literal["metric", "dimension", "table", "column"]
    entity_id: str
    description: str | None = None


class MetricDefinition(SemanticModel):
    """Enhanced metric definition - authoritative semantic contract."""

    # Identity
    id: str = Field(min_length=1, max_length=100, description="Unique metric ID")
    version: str = Field(min_length=1, max_length=50, description="Semantic version")
    name: str = Field(min_length=1, max_length=200, description="Display name")
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names and phrases for resolution",
    )

    # Description
    description: str = Field(default="", description="Business description")
    business_context: str | None = Field(
        default=None,
        description="When and why to use this metric",
    )
    interpretation_guide: str | None = Field(
        default=None,
        description="How to interpret values",
    )

    # Computation
    formula: MetricFormula = Field(description="Authoritative computation formula")
    unit: str = Field(description="Display unit (e.g., USD, count, %)")
    aggregation: AggregationType = Field(description="Primary aggregation type")
    semantic_type: SemanticType = Field(description="Semantic data type")

    # Grains
    supported_grains: list[MetricSupportedGrain] = Field(
        description="Supported time grains",
    )
    default_grain: TimeGrain = Field(description="Default aggregation grain")

    # Dimensions
    required_dimensions: list[str] = Field(
        description="Dimensions required for this metric",
    )
    optional_dimensions: list[str] = Field(
        default_factory=list,
        description="Optional dimensions",
    )
    incompatible_dimensions: list[str] = Field(
        default_factory=list,
        description="Dimensions that cannot be used together",
    )

    # Join paths
    allowed_join_paths: list[MetricJoinPath] = Field(
        default_factory=list,
        description="Valid join paths",
    )
    default_join_path: str | None = Field(
        default=None,
        description="Default join path ID",
    )

    # Source
    source_table: str = Field(description="Primary source table")
    source_columns: list[str] = Field(default_factory=list, description="Source columns")

    # Time semantics
    time_interpretation: Literal[
        "transaction_date",
        "business_date",
        "reporting_date",
        "fiscal_period",
    ] = "business_date"
    fiscal_year_start_month: int = Field(
        default=1,
        ge=1,
        le=12,
        description="Start month of fiscal year",
    )

    # Availability
    availability: Availability = Field(
        description="Date range availability",
    )
    freshness: Freshness | None = Field(
        default=None,
        description="Data freshness information",
    )

    # Classification
    classification: DataClassification = DataClassification.INTERNAL
    policy_tags: list[str] = Field(
        default_factory=list,
        description="Policy tags for access control",
    )

    # Business rules
    business_rules: list[MetricBusinessRule] = Field(
        default_factory=list,
        description="Associated business rules",
    )
    validation_rules: list[str] = Field(
        default_factory=list,
        description="Validation rule IDs",
    )

    # Ownership
    owner: str = Field(description="Business owner")
    owner_team: str | None = None
    documentation_url: str | None = None

    # Lineage
    lineage: list[MetricLineageReference] = Field(
        default_factory=list,
        description="Upstream/downstream lineage",
    )

    # Behavior
    unavailable_behavior: Literal["error", "null", "zero", "partial"] = "error"
    caution: str | None = Field(
        default=None,
        description="Caution notes for usage",
    )

    # Computed helpers
    def supports_grain(self, grain: TimeGrain) -> bool:
        """Check if metric supports given grain."""
        return any(g.grain == grain and g.available for g in self.supported_grains)

    def covers(self, start: date | None, end: date | None) -> bool:
        """Check if metric availability covers given date range."""
        return self.availability.covers(start, end)

    def matches_alias(self, alias: str) -> bool:
        """Check if alias matches metric."""
        alias_lower = alias.lower()
        return (
            alias_lower == self.name.lower()
            or alias_lower == self.id.lower()
            or alias_lower in [a.lower() for a in self.aliases]
        )


# =============================================================================
# Package identity
# =============================================================================


class PackageIdentity(SemanticModel):
    """Identity information for a semantic package."""

    id: str = Field(description="Package identifier")
    version: str = Field(description="Semantic version (semver)")
    title: str = Field(description="Package title")
    description: str = Field(default="", description="Package description")
    domain: str = Field(description="Business domain")

    # Configuration
    timezone: str = Field(default="UTC", description="Default timezone")
    currency: str = Field(default="USD", description="Default currency")
    fiscal_year_start_month: int = Field(default=1, ge=1, le=12)

    # Source data
    source_snapshot_alias: str = Field(
        description="Default data snapshot alias",
    )
    default_snapshot: str = Field(
        description="Default snapshot identifier",
    )

    # Metadata
    owner: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


# =============================================================================
# Full semantic package
# =============================================================================


class SemanticPackageV2(SemanticModel):
    """Complete semantic package v2."""

    package: PackageIdentity
    metrics: list[MetricDefinition]
    dimensions: list[DimensionDefinition]

    # Join policies
    join_policies: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Global join policies",
    )

    # Business rules
    business_rules: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Global business rules",
    )

    # Quality rules
    quality_rules: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Data quality rules",
    )

    # Access policies
    access_policies: dict[str, dict[str, list[str]]] = Field(
        default_factory=dict,
        description="Role-based access policies",
    )

    # Content integrity
    content_hash: str = Field(
        default="",
        description="SHA-256 hash of package content",
    )

    @field_validator("metrics")
    @classmethod
    def unique_metric_ids(cls, v: list[MetricDefinition]) -> list[MetricDefinition]:
        ids = [m.id for m in v]
        if len(ids) != len(set(ids)):
            raise ValueError("metric IDs must be unique")
        return v

    @field_validator("dimensions")
    @classmethod
    def unique_dimension_ids(
        cls, v: list[DimensionDefinition]
    ) -> list[DimensionDefinition]:
        ids = [d.id for d in v]
        if len(ids) != len(set(ids)):
            raise ValueError("dimension IDs must be unique")
        return v

    def metric(self, metric_id: str) -> MetricDefinition:
        """Get metric by ID."""
        for metric in self.metrics:
            if metric.id == metric_id:
                return metric
        raise KeyError(f"unknown metric: {metric_id}")

    def dimension(self, dimension_id: str) -> DimensionDefinition:
        """Get dimension by ID."""
        for dimension in self.dimensions:
            if dimension.id == dimension_id:
                return dimension
        raise KeyError(f"unknown dimension: {dimension_id}")

    def find_metric_by_alias(self, alias: str) -> MetricDefinition | None:
        """Find metric by alias."""
        alias_lower = alias.lower()
        for metric in self.metrics:
            if metric.matches_alias(alias_lower):
                return metric
        return None

    def find_dimension_by_alias(self, alias: str) -> DimensionDefinition | None:
        """Find dimension by alias."""
        alias_lower = alias.lower()
        for dimension in self.dimensions:
            if alias_lower == dimension.id.lower():
                return dimension
            if alias_lower in [a.lower() for a in dimension.aliases]:
                return dimension
        return None

    def validate_metric_reference(
        self,
        metric_id: str,
        dimension_ids: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate metric reference returns (valid, list of issues)."""
        issues = []

        try:
            metric = self.metric(metric_id)
        except KeyError:
            return False, [f"unknown metric: {metric_id}"]

        # Check availability
        if not metric.covers(start_date, end_date):
            issues.append(
                f"metric {metric_id} not available for {start_date} to {end_date}"
            )

        # Check required dimensions
        for dim_id in metric.required_dimensions:
            if dim_id not in dimension_ids:
                issues.append(f"missing required dimension: {dim_id}")

        # Check incompatible dimensions
        for dim_id in metric.incompatible_dimensions:
            if dim_id in dimension_ids:
                issues.append(f"incompatible dimension: {dim_id}")

        # Check grain support
        # (would need grain parameter)

        return len(issues) == 0, issues
