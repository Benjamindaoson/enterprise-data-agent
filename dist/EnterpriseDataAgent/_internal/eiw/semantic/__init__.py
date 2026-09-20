"""Semantic package module for Enterprise Data Agent.

Provides:
- Semantic Layer v2 with enhanced metric and dimension definitions
- Package loading and validation
- Metric resolution
"""

from eiw.semantic.package import (
    SemanticPackage,
    SemanticModel,
    MetricDefinition as MetricDefinitionV1,
    DimensionDefinition as DimensionDefinitionV1,
    Availability,
    PackageIdentity,
    load_semantic_package,
)
from eiw.semantic.loader import (
    load_semantic_package_v2,
    load_any_semantic_package,
    get_package_domains,
    load_domain_package,
    SemanticPackageV2,
)
from eiw.semantic.v2 import (
    MetricDefinition,
    DimensionDefinition,
    SemanticPackageV2 as PackageV2,
    MetricFormula,
    MetricJoinPath,
    MetricSupportedGrain,
    MetricBusinessRule,
    MetricLineageReference,
    DimensionHierarchy,
    DataClassification,
    DataClassification as SemanticDataClassification,
    TimeGrain,
    AggregationType,
    SemanticType,
    Availability,
    Availability as AvailabilityV2,
    Freshness,
    PackageIdentity as PackageIdentityV2,
    SemanticModel as SemanticModelV2,
)
from eiw.semantic.resolver import (
    SemanticResolver,
    SemanticResolutionInput,
    SemanticResolutionResult,
)

__all__ = [
    # Legacy
    "SemanticPackage",
    "SemanticModel",
    "MetricDefinitionV1",
    "DimensionDefinitionV1",
    "Availability",
    "PackageIdentity",
    "load_semantic_package",
    # Loader
    "load_semantic_package_v2",
    "load_any_semantic_package",
    "get_package_domains",
    "load_domain_package",
    "SemanticPackageV2",
    # V2 types
    "MetricDefinition",
    "DimensionDefinition",
    "PackageV2",
    "MetricFormula",
    "MetricJoinPath",
    "MetricSupportedGrain",
    "MetricBusinessRule",
    "MetricLineageReference",
    "DimensionHierarchy",
    "DataClassification",
    "SemanticDataClassification",
    "TimeGrain",
    "AggregationType",
    "SemanticType",
    "Availability",
    "AvailabilityV2",
    "Freshness",
    "PackageIdentityV2",
    "SemanticModelV2",
    # Resolver
    "SemanticResolver",
    "SemanticResolutionInput",
    "SemanticResolutionResult",
]
