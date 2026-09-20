"""Intent Resolver - Resolves business questions to structured intent.

This module provides:
- Business question parsing
- Metric and dimension extraction
- Time range resolution
- Ambiguity detection
- Clarification requests
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from eiw.agent.provider import ModelProvider, DeterministicProvider, ProviderConfig
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "intent_resolver")


# =============================================================================
# Intent Enums
# =============================================================================


class AnalysisType(str, Enum):
    """Types of analysis that can be requested."""

    DESCRIPTIVE = "descriptive"  # What happened
    DIAGNOSTIC = "diagnostic"  # Why did it happen
    PREDICTIVE = "predictive"  # What will happen
    PRESCRIPTIVE = "prescriptive"  # What should we do
    COMPARISON = "comparison"  # Compare periods/segments
    TREND = "trend"  # Trend analysis
    CONTRIBUTION = "contribution"  # Contribution decomposition
    VARIANCE = "variance"  # Budget variance
    ANOMALY = "anomaly"  # Anomaly detection
    DRILLDOWN = "drilldown"  # Detailed breakdown


class RequestedOutput(str, Enum):
    """Requested output formats."""

    TEXT = "text"  # Natural language answer
    TABLE = "table"  # Data table
    CHART = "chart"  # Visualization
    DASHBOARD = "dashboard"  # Multiple charts
    REPORT = "report"  # Formal report
    CSV = "csv"  # Export data


class AmbiguityType(str, Enum):
    """Types of ambiguity in business questions."""

    METRIC = "metric"  # Unclear which metric
    TIME_RANGE = "time_range"  # Unclear time period
    DIMENSION = "dimension"  # Unclear grouping
    GRANULARITY = "granularity"  # Unclear aggregation level
    ENTITY = "entity"  # Unclear entity
    COMPARISON = "comparison"  # Unclear comparison baseline


# =============================================================================
# Resolved Intent Model
# =============================================================================


class ResolvedBusinessIntent(BaseModel):
    """Resolved business intent from a natural language question."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(description="Core business objective")
    domain: str = Field(description="Business domain (finance, sales, etc.)")
    analysis_type: AnalysisType = Field(description="Type of analysis requested")

    # Metrics
    metric_candidates: list[str] = Field(
        default_factory=list,
        description="Candidate metric IDs"
    )
    selected_metrics: list[str] = Field(
        default_factory=list,
        description="Selected metric IDs after resolution"
    )

    # Dimensions
    dimension_candidates: list[str] = Field(
        default_factory=list,
        description="Candidate dimension IDs"
    )
    selected_dimensions: list[str] = Field(
        default_factory=list,
        description="Selected dimension IDs"
    )

    # Entities and Filters
    entities: dict[str, Any] = Field(
        default_factory=dict,
        description="Entity filters (region, product, etc.)"
    )

    # Time
    time_range_start: date | None = Field(
        default=None,
        description="Start of time range"
    )
    time_range_end: date | None = Field(
        default=None,
        description="End of time range"
    )
    time_granularity: str | None = Field(
        default=None,
        description="Time granularity (day, week, month, etc.)"
    )

    # Comparison
    comparison_baseline: str | None = Field(
        default=None,
        description="Comparison baseline description"
    )
    comparison_period_start: date | None = Field(
        default=None,
        description="Comparison period start"
    )
    comparison_period_end: date | None = Field(
        default=None,
        description="Comparison period end"
    )

    # Output
    requested_output: RequestedOutput = Field(
        default=RequestedOutput.TEXT,
        description="Requested output format"
    )

    # Ambiguity
    ambiguities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detected ambiguities"
    )
    requires_clarification: bool = Field(
        default=False,
        description="Whether clarification is required"
    )

    # Context
    user_roles: list[str] = Field(
        default_factory=list,
        description="User roles for permission checking"
    )
    user_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional user context"
    )

    # Assumptions and limitations
    assumptions: list[str] = Field(
        default_factory=list,
        description="Made assumptions"
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Known limitations"
    )


class ClarificationQuestion(BaseModel):
    """A clarification question to ask the user."""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(description="Unique question identifier")
    ambiguity_type: AmbiguityType = Field(description="Type of ambiguity")
    question: str = Field(description="Clarification question text")
    options: list[str] = Field(
        default_factory=list,
        description="Possible answer options"
    )
    context: str = Field(
        default="",
        description="Why this clarification is needed"
    )


class IntentResolutionResult(BaseModel):
    """Result of intent resolution."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(description="Whether resolution succeeded")
    intent: ResolvedBusinessIntent | None = Field(
        default=None,
        description="Resolved intent"
    )
    clarification_needed: bool = Field(
        default=False,
        description="Whether clarification is needed"
    )
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="Questions to ask user"
    )
    error: str | None = Field(
        default=None,
        description="Error message if failed"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Resolution confidence"
    )


# =============================================================================
# Intent Resolver
# =============================================================================


class IntentResolver:
    """Resolves business questions into structured intent.

    This resolver:
    1. Parses natural language questions
    2. Extracts metrics, dimensions, entities
    3. Resolves time expressions
    4. Detects ambiguities
    5. Requests clarification when needed
    """

    def __init__(
        self,
        provider: ModelProvider | None = None,
        semantic_package: Any | None = None,
    ):
        """Initialize intent resolver.

        Args:
            provider: Model provider for resolution
            semantic_package: Semantic package for metric resolution
        """
        self._provider = provider or DeterministicProvider(ProviderConfig())
        self._semantic_package = semantic_package
        self._resolution_count = 0

    @property
    def resolution_count(self) -> int:
        """Number of resolutions performed."""
        return self._resolution_count

    async def resolve(
        self,
        question: str,
        domain: str | None = None,
        user_roles: list[str] | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> IntentResolutionResult:
        """Resolve a business question to structured intent.

        Args:
            question: Natural language business question
            domain: Business domain hint
            user_roles: User roles for permission checking
            user_context: Additional user context

        Returns:
            Intent resolution result
        """
        with trace_span("intent.resolve", {
            "question_length": len(question),
            "domain": domain,
        }):
            self._resolution_count += 1

            try:
                # Parse and extract intent components
                parsed = await self._parse_question(
                    question=question,
                    domain=domain,
                    user_roles=user_roles or [],
                )

                if parsed.requires_clarification:
                    return IntentResolutionResult(
                        success=False,
                        clarification_needed=True,
                        clarification_questions=parsed.clarification_questions,
                        confidence=0.0,
                    )

                return IntentResolutionResult(
                    success=True,
                    intent=parsed,
                    confidence=self._calculate_confidence(parsed),
                )

            except Exception as e:
                logger.error(f"Intent resolution failed: {e}")
                return IntentResolutionResult(
                    success=False,
                    error=str(e),
                )

    async def _parse_question(
        self,
        question: str,
        domain: str | None,
        user_roles: list[str],
    ) -> ResolvedBusinessIntent:
        """Parse question into structured intent.

        Args:
            question: Business question
            domain: Domain hint
            user_roles: User roles

        Returns:
            Resolved business intent
        """
        # Use provider for complex parsing
        prompt = self._build_parsing_prompt(question, domain)

        response = await self._provider.complete(prompt)
        if response.error:
            raise Exception(f"Provider error: {response.error}")

        # Parse response into intent
        intent = self._parse_provider_response(
            response.content,
            question,
            domain,
            user_roles,
        )

        # Check for ambiguities
        ambiguities = self._detect_ambiguities(intent, question)
        if ambiguities:
            intent.requires_clarification = True
            intent.ambiguities = ambiguities

        return intent

    def _build_parsing_prompt(
        self,
        question: str,
        domain: str | None,
    ) -> str:
        """Build prompt for intent parsing.

        Args:
            question: Business question
            domain: Domain hint

        Returns:
            Parsing prompt
        """
        domain_hint = f"Domain: {domain}\n" if domain else ""

        return f"""Parse this business question into structured intent.

{domain_hint}
Question: {question}

Output JSON with:
- objective: What the user wants to understand
- analysis_type: descriptive, diagnostic, comparison, trend, contribution, variance, anomaly, drilldown
- metric_candidates: Possible metrics (as short IDs)
- dimension_candidates: Possible dimensions
- entities: Filters specified (region, product, etc.)
- time_range: What time period is mentioned
- comparison_baseline: What comparison is requested
- requested_output: text, table, chart, dashboard, report

If ambiguous, note it in the output.
Respond with JSON only."""

    def _parse_provider_response(
        self,
        content: str,
        question: str,
        domain: str | None,
        user_roles: list[str],
    ) -> ResolvedBusinessIntent:
        """Parse provider response into intent.

        Args:
            content: Provider response content
            question: Original question
            domain: Domain
            user_roles: User roles

        Returns:
            Resolved intent
        """
        import json

        # Safety check: if content looks like an error message, use defaults
        if not content or len(content) < 10 or content.startswith("'") and "object has no attribute" in content:
            logger.warning(f"Provider returned invalid content, using defaults")
            return self._create_default_intent(question, domain, user_roles)

        # Extract JSON from response
        data = {}
        try:
            # Try to find JSON in response
            json_str = self._extract_json(content)
            data = json.loads(json_str)
        except Exception:
            # Fallback - no valid JSON, use defaults
            logger.warning(f"Could not parse JSON from provider response: {content[:100]}")
            return self._create_default_intent(question, domain, user_roles)

        # Build intent from parsed data
        # Handle both enum and string analysis_type
        analysis_type_str = data.get("analysis_type", "descriptive")
        try:
            if isinstance(analysis_type_str, str):
                analysis_type = AnalysisType(analysis_type_str)
            elif hasattr(analysis_type_str, 'value'):
                analysis_type = AnalysisType(analysis_type_str.value)
            else:
                analysis_type = AnalysisType.DESCRIPTIVE
        except (ValueError, AttributeError):
            analysis_type = AnalysisType.DESCRIPTIVE

        requested_output_str = data.get("requested_output", "text")
        try:
            if isinstance(requested_output_str, str):
                requested_output = RequestedOutput(requested_output_str)
            elif hasattr(requested_output_str, 'value'):
                requested_output = RequestedOutput(requested_output_str.value)
            else:
                requested_output = RequestedOutput.TEXT
        except (ValueError, AttributeError):
            requested_output = RequestedOutput.TEXT

        return ResolvedBusinessIntent(
            objective=data.get("objective", question),
            domain=domain or data.get("domain", "unknown"),
            analysis_type=analysis_type,
            metric_candidates=data.get("metric_candidates", []),
            selected_metrics=data.get("selected_metrics", []),
            dimension_candidates=data.get("dimension_candidates", []),
            selected_dimensions=data.get("selected_dimensions", []),
            entities=data.get("entities", {}),
            time_range_start=data.get("time_range_start"),
            time_range_end=data.get("time_range_end"),
            time_granularity=data.get("time_granularity"),
            comparison_baseline=data.get("comparison_baseline"),
            requested_output=requested_output,
            user_roles=user_roles,
        )

    def _create_default_intent(
        self,
        question: str,
        domain: str | None,
        user_roles: list[str],
    ) -> ResolvedBusinessIntent:
        """Create a default intent when parsing fails.

        Args:
            question: Original question
            domain: Domain
            user_roles: User roles

        Returns:
            Default intent
        """
        return ResolvedBusinessIntent(
            objective=question,
            domain=domain or "general",
            analysis_type=AnalysisType.DESCRIPTIVE,
            metric_candidates=[],
            selected_metrics=[],
            dimension_candidates=[],
            selected_dimensions=[],
            entities={},
            time_range_start=None,
            time_range_end=None,
            time_granularity=None,
            comparison_baseline=None,
            requested_output=RequestedOutput.TEXT,
            user_roles=user_roles,
        )

    def _extract_json(self, content: str) -> str:
        """Extract JSON from content.

        Args:
            content: Response content

        Returns:
            Extracted JSON string
        """
        content = content.strip()

        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    def _detect_ambiguities(
        self,
        intent: ResolvedBusinessIntent,
        question: str,
    ) -> list[dict[str, Any]]:
        """Detect ambiguities in resolved intent.

        Args:
            intent: Resolved intent
            question: Original question

        Returns:
            List of detected ambiguities
        """
        ambiguities = []

        # Check for multiple metric candidates
        if len(intent.metric_candidates) > 1:
            ambiguities.append({
                "type": AmbiguityType.METRIC.value,
                "message": f"Multiple metrics possible: {intent.metric_candidates}",
                "question": "Which metric are you interested in?",
            })

        # Check for missing time range
        if not intent.time_range_start and not intent.time_range_end:
            # Common time expressions to check
            time_keywords = ["yesterday", "last week", "last month", "quarter", "q1", "q2", "q3", "q4", "ytd", "mtd"]
            if any(kw in question.lower() for kw in time_keywords):
                ambiguities.append({
                    "type": AmbiguityType.TIME_RANGE.value,
                    "message": "Time period detected but not fully resolved",
                    "question": "What specific time period do you mean?",
                })

        # Check for missing dimension in comparison
        if intent.comparison_baseline and not intent.selected_dimensions:
            ambiguities.append({
                "type": AmbiguityType.DIMENSION.value,
                "message": "Comparison requested but no grouping dimension specified",
                "question": "How would you like to break down the comparison?",
            })

        return ambiguities

    def _calculate_confidence(self, intent: ResolvedBusinessIntent) -> float:
        """Calculate resolution confidence.

        Args:
            intent: Resolved intent

        Returns:
            Confidence score 0-1
        """
        score = 0.5  # Base score

        # Higher confidence if metrics are selected
        if intent.selected_metrics:
            score += 0.15

        # Higher confidence if time range is complete
        if intent.time_range_start and intent.time_range_end:
            score += 0.15

        # Lower confidence if ambiguous
        if intent.ambiguities:
            score -= 0.1 * len(intent.ambiguities)

        return max(0.0, min(1.0, score))

    def resolve_time_expression(
        self,
        expression: str,
        reference_date: date | None = None,
    ) -> tuple[date | None, date | None]:
        """Resolve a natural language time expression to dates.

        Args:
            expression: Time expression (e.g., "last month", "Q2 2024")
            reference_date: Reference date for relative expressions

        Returns:
            Tuple of (start_date, end_date)
        """
        from datetime import timedelta

        ref = reference_date or date.today()
        expr_lower = expression.lower()

        # Simple pattern matching for common expressions
        if "yesterday" in expr_lower:
            start = ref - timedelta(days=1)
            return start, start

        if "last week" in expr_lower:
            start = ref - timedelta(weeks=1)
            return start, ref

        if "last month" in expr_lower:
            # Approximate - go back 30 days
            start = ref - timedelta(days=30)
            return start, ref

        if "q1" in expr_lower or "q1 2024" in expr_lower:
            from datetime import date as d
            return d(2024, 1, 1), d(2024, 3, 31)

        if "q2" in expr_lower or "q2 2024" in expr_lower:
            from datetime import date as d
            return d(2024, 4, 1), d(2024, 6, 30)

        # Default: return reference date as single day
        return ref, ref


def create_intent_resolver(
    provider: ModelProvider | None = None,
    semantic_package: Any | None = None,
) -> IntentResolver:
    """Create an intent resolver.

    Args:
        provider: Model provider
        semantic_package: Semantic package

    Returns:
        Intent resolver instance
    """
    return IntentResolver(provider=provider, semantic_package=semantic_package)
