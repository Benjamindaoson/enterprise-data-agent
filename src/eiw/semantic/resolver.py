"""Semantic resolver for resolving business questions to semantic entities.

Integrates with:
- Semantic packages (metrics, dimensions)
- Knowledge base (definitions, glossary)
- OTel for tracing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from eiw.domain.models import ResolvedMetric, ResolvedBusinessIntent
from eiw.knowledge.base import (
    KnowledgeBase,
    KnowledgeRetrievalQuery,
    KnowledgeRetrievalResult,
    get_knowledge_base,
)
from eiw.observability.logging import get_structured_logger, log_task_event
from eiw.observability.otel import trace_span
from eiw.semantic.v2 import (
    SemanticPackageV2,
    MetricDefinition,
    DimensionDefinition,
)


logger = get_structured_logger(__name__, "semantic_resolver")


@dataclass
class SemanticResolutionInput:
    """Input for semantic resolution."""

    business_question: str
    domain_id: str | None = None
    user_roles: list[str] = field(default_factory=list)
    time_range_start: date | None = None
    time_range_end: date | None = None


@dataclass
class SemanticResolutionResult:
    """Result of semantic resolution."""

    resolved_intent: ResolvedBusinessIntent
    resolved_metrics: list[MetricDefinition]
    resolved_dimensions: list[DimensionDefinition]
    knowledge_results: KnowledgeRetrievalResult
    resolution_confidence: float
    ambiguities: list[str] = field(default_factory=list)
    requires_clarification: bool = False


class SemanticResolver:
    """Resolves business questions to semantic entities.

    This resolver:
    1. Loads and validates semantic packages
    2. Resolves metric and dimension references from natural language
    3. Retrieves relevant knowledge (definitions, examples)
    4. Returns structured intent with confidence scores
    """

    def __init__(
        self,
        semantic_package: SemanticPackageV2,
        knowledge_base: KnowledgeBase | None = None,
    ) -> None:
        """Initialize semantic resolver.

        Args:
            semantic_package: The semantic package to use for resolution
            knowledge_base: Optional knowledge base for retrieval
        """
        self.package = semantic_package
        self.knowledge_base = knowledge_base or get_knowledge_base()

    def resolve(self, input_data: SemanticResolutionInput) -> SemanticResolutionResult:
        """Resolve a business question to semantic entities.

        Args:
            input_data: Input containing the business question

        Returns:
            Resolution result with resolved metrics, dimensions, and knowledge
        """
        with trace_span("semantic.resolve", {
            "domain_id": input_data.domain_id or self.package.package.id,
            "semantic_package_id": self.package.package.id,
            "semantic_package_version": self.package.package.version,
        }):
            # Step 1: Extract potential metric references from question
            metric_refs = self._extract_metric_references(input_data.business_question)

            # Step 2: Resolve metrics
            resolved_metrics: list[MetricDefinition] = []
            resolved_metric_responses: list[ResolvedMetric] = []
            ambiguities: list[str] = []

            for ref in metric_refs:
                with trace_span("metric.retrieve", {
                    "metric_ref": ref,
                }):
                    metric, confidence = self._resolve_metric(ref)
                    if metric:
                        resolved_metrics.append(metric)
                        resolved_metric_responses.append(ResolvedMetric(
                            metric_id=metric.id,
                            confidence=confidence,
                            interpretation=f"Resolved '{ref}' to metric '{metric.name}'",
                        ))
                    else:
                        ambiguities.append(f"Could not resolve metric: {ref}")

            # Step 3: Resolve dimensions
            resolved_dimensions = self._resolve_dimensions(
                input_data.business_question,
                resolved_metrics,
            )

            # Step 4: Retrieve relevant knowledge
            knowledge_results = self._retrieve_knowledge(
                input_data.business_question,
                [m.id for m in resolved_metrics],
                input_data.domain_id,
            )

            # Step 5: Build intent
            intent = ResolvedBusinessIntent(
                objective=input_data.business_question,
                metrics=resolved_metric_responses,
                dimension_filters={},  # Would be populated from dimension resolution
                primary_period_start=input_data.time_range_start,
                primary_period_end=input_data.time_range_end,
                ambiguities=ambiguities,
                requires_clarification=len(ambiguities) > 0 and not resolved_metrics,
            )

            # Calculate overall confidence
            if resolved_metrics:
                avg_confidence = sum(
                    m.confidence for m in resolved_metric_responses
                ) / len(resolved_metric_responses)
            else:
                avg_confidence = 0.0

            log_task_event(
                event="semantic_resolved",
                message=f"Resolved {len(resolved_metrics)} metrics from question",
                task_id=None,
                component="semantic_resolver",
                status="OK",
                metric_ids=[m.id for m in resolved_metrics],
                dimension_ids=[d.id for d in resolved_dimensions],
            )

            return SemanticResolutionResult(
                resolved_intent=intent,
                resolved_metrics=resolved_metrics,
                resolved_dimensions=resolved_dimensions,
                knowledge_results=knowledge_results,
                resolution_confidence=avg_confidence,
                ambiguities=ambiguities,
                requires_clarification=intent.requires_clarification,
            )

    def _extract_metric_references(self, question: str) -> list[str]:
        """Extract potential metric references from question.

        This is a simple extraction based on the semantic package.
        In production, this would use NLP/LLM.
        """
        question_lower = question.lower()
        words = set(question_lower.split())

        refs = []

        # Check each metric for matches
        for metric in self.package.metrics:
            # Check ID
            if metric.id.lower() in question_lower:
                refs.append(metric.id)
            # Check name
            elif metric.name.lower() in question_lower:
                refs.append(metric.id)
            # Check aliases
            else:
                for alias in metric.aliases:
                    if alias.lower() in question_lower:
                        refs.append(metric.id)
                        break

        return list(set(refs))

    def _resolve_metric(self, metric_ref: str) -> tuple[MetricDefinition | None, float]:
        """Resolve a metric reference to a metric definition.

        Args:
            metric_ref: Metric reference (ID, name, or alias)

        Returns:
            Tuple of (resolved metric, confidence score)
        """
        # Try exact ID match
        try:
            metric = self.package.metric(metric_ref)
            return metric, 1.0
        except KeyError:
            pass

        # Try alias match
        metric = self.package.find_metric_by_alias(metric_ref)
        if metric:
            return metric, 0.95

        # Try partial match
        for m in self.package.metrics:
            if metric_ref.lower() in m.id.lower() or metric_ref.lower() in m.name.lower():
                return m, 0.8

        return None, 0.0

    def _resolve_dimensions(
        self,
        question: str,
        metrics: list[MetricDefinition],
    ) -> list[DimensionDefinition]:
        """Resolve dimension references from question.

        Args:
            question: Business question
            metrics: Resolved metrics (for context)

        Returns:
            List of resolved dimensions
        """
        question_lower = question.lower()
        resolved = []

        for dimension in self.package.dimensions:
            # Check ID
            if dimension.id.lower() in question_lower:
                resolved.append(dimension)
                continue

            # Check name
            if dimension.name.lower() in question_lower:
                resolved.append(dimension)
                continue

            # Check aliases
            for alias in dimension.aliases:
                if alias.lower() in question_lower:
                    resolved.append(dimension)
                    break

        return resolved

    def _retrieve_knowledge(
        self,
        question: str,
        metric_ids: list[str],
        domain_id: str | None,
    ) -> KnowledgeRetrievalResult:
        """Retrieve relevant knowledge for the question.

        Args:
            question: Business question
            metric_ids: Resolved metric IDs
            domain_id: Domain ID

        Returns:
            Knowledge retrieval results
        """
        with trace_span("knowledge.retrieve", {
            "query_type": "general",
            "domain_id": domain_id or self.package.package.id,
        }):
            query = KnowledgeRetrievalQuery(
                query_text=question,
                domain_ids=[domain_id] if domain_id else [],
                related_metric_ids=metric_ids,
                max_results=5,
            )

            results = self.knowledge_base.retrieve(query)

            log_task_event(
                event="knowledge_retrieved",
                message=f"Retrieved {len(results.items)} knowledge items",
                task_id=None,
                component="knowledge_retriever",
                status="OK",
            )

            return results

    def validate_metric_reference(
        self,
        metric_id: str,
        dimension_ids: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate a metric reference.

        Args:
            metric_id: Metric ID to validate
            dimension_ids: Dimension IDs to use
            start_date: Start date for availability check
            end_date: End date for availability check

        Returns:
            Tuple of (is_valid, list of issues)
        """
        return self.package.validate_metric_reference(
            metric_id,
            dimension_ids,
            start_date,
            end_date,
        )
