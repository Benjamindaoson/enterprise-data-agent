"""Intent Recognition and Resolution.

This module handles:
- Natural language understanding
- Business intent classification
- Metric/Dimension/Entity/Time extraction
- Semantic disambiguation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class IntentType(Enum):
    """Business intent classification."""

    METRIC_QUERY = "metric_query"           # KPI / metric lookup
    TREND_ANALYSIS = "trend_analysis"       # Time series analysis
    COMPARISON = "comparison"               # Period/region comparison
    CONTRIBUTION = "contribution"           # Driver analysis
    ATTRIBUTION = "attribution"             # Cause analysis
    ANOMALY_DETECTION = "anomaly_detection" # Anomaly investigation
    EXPLAIN = "explain"                     # Metric definition/explanation
    FORECAST = "forecast"                   # Forward projection
    BUDGET_VARIANCE = "budget_variance"     # Budget vs actual
    drilldown = "drilldown"                 # Multi-dimensional drill
    nl2sql = "nl2sql"                       # Ad-hoc SQL query
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Resolved business intent."""

    intent_type: IntentType
    confidence: float
    primary_metrics: list[str] = field(default_factory=list)
    secondary_metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    filters: dict[str, list[str]] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)
    primary_period_start: date | None = None
    primary_period_end: date | None = None
    comparison_period_start: date | None = None
    comparison_period_end: date | None = None
    granularity: str | None = None  # day, week, month, quarter, year
    requires_nl2sql: bool = False
    ambiguities: list[str] = field(default_factory=list)
    requires_clarification: bool = False
    clarification_questions: list[str] = field(default_factory=list)
    raw_components: dict[str, Any] = field(default_factory=dict)

    def to_context(self) -> dict[str, Any]:
        """Convert to context dict for downstream processing."""
        return {
            "intent_type": self.intent_type.value,
            "confidence": self.confidence,
            "primary_metrics": self.primary_metrics,
            "secondary_metrics": self.secondary_metrics,
            "dimensions": self.dimensions,
            "filters": self.filters,
            "entities": self.entities,
            "primary_period": {
                "start": self.primary_period_start.isoformat() if self.primary_period_start else None,
                "end": self.primary_period_end.isoformat() if self.primary_period_end else None,
            },
            "comparison_period": {
                "start": self.comparison_period_start.isoformat() if self.comparison_period_start else None,
                "end": self.comparison_period_end.isoformat() if self.comparison_period_end else None,
            },
            "granularity": self.granularity,
            "requires_nl2sql": self.requires_nl2sql,
            "ambiguities": self.ambiguities,
            "requires_clarification": self.requires_clarification,
        }


class IntentResolver:
    """Resolves natural language business questions into structured intents.

    This is the first step in the Enterprise Data Agent pipeline:
    Natural Language → Structured Intent → Semantic Resolution → Planning
    """

    # Time period patterns
    TIME_PATTERNS = {
        "month_year": re.compile(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})",
            re.I,
        ),
        "relative": re.compile(
            r"(last|previous|past|current|this|next)\s+(month|quarter|year|week|day|\d+\s+days?)",
            re.I,
        ),
        "range": re.compile(
            r"(from|between)\s+(\d{4}-\d{2}-\d{2})\s+(to|until)\s+(\d{4}-\d{2}-\d{2})",
            re.I,
        ),
        "yoy": re.compile(r"(year[- ]over[- ]year|yoy|y\/y)", re.I),
        "mom": re.compile(r"(month[- ]over[- ]month|mom|m\/m)", re.I),
        "wow": re.compile(r"(week[- ]over[- ]week|wow|w\/w)", re.I),
    }

    # Intent keywords
    INTENT_KEYWORDS = {
        IntentType.METRIC_QUERY: [
            "show", "what is", "how much", "total", "sum", "count",
            "value", "amount", "revenue", "profit", "sales",
        ],
        IntentType.TREND_ANALYSIS: [
            "trend", "over time", "growth", "decline", "trajectory",
            "pattern", "historical", "progress",
        ],
        IntentType.COMPARISON: [
            "compare", "versus", "vs", "difference", "change",
            "increase", "decrease", "growth rate", "decline",
        ],
        IntentType.CONTRIBUTION: [
            "contribute", "driver", "impact", "breakdown", "decompose",
            "attribution", "which", "top", "largest",
        ],
        IntentType.ATTRIBUTION: [
            "why", "cause", "reason", "attributed to", "because",
            "due to", "explains",
        ],
        IntentType.ANOMALY_DETECTION: [
            "anomaly", "unusual", "unexpected", "abnormal", "outlier",
            "spike", "dip", "surge", "drop",
        ],
        IntentType.EXPLAIN: [
            "what does", "definition", "mean", "how is", "calculated",
            "formula", "explain", "explain",
        ],
        IntentType.BUDGET_VARIANCE: [
            "budget", "variance", "actual", "target", "plan",
            "forecast vs actual", "budget vs",
        ],
        IntentType.drilldown: [
            "drill down", "break down", "detail", "by region",
            "by product", "by category", "split",
        ],
    }

    # Metric keywords (will be enriched by semantic layer)
    METRIC_KEYWORDS = {
        "revenue": ["revenue", "sales amount", "total sales", "net revenue"],
        "gross_profit": ["gross profit", "gross margin"],
        "profit_margin": ["margin", "profit rate", "profitability"],
        "order_count": ["orders", "order count", "transactions"],
        "customer_count": ["customers", "customer count", "new customers"],
        "average_order_value": ["aov", "average order", "avg order value"],
        "conversion_rate": ["conversion", "conversion rate"],
        "inventory": ["inventory", "stock", "on hand"],
        "cost": ["cost", "spend", "expense"],
    }

    # Dimension keywords
    DIMENSION_KEYWORDS = {
        "region": ["region", "area", "territory", "zone"],
        "product": ["product", "sku", "item", "category"],
        "customer": ["customer", "client", "account"],
        "channel": ["channel", "sales channel", "distribution"],
        "time": ["month", "quarter", "year", "week", "day", "period"],
        "store": ["store", "location", "outlet"],
        "supplier": ["supplier", "vendor", "partner"],
    }

    def __init__(self, semantic_package: Any | None = None) -> None:
        """Initialize resolver with optional semantic package."""
        self.semantic_package = semantic_package

    def resolve(self, question: str) -> IntentResult:
        """Resolve a business question into structured intent.

        Args:
            question: Natural language business question

        Returns:
            IntentResult with classified intent and extracted components
        """
        question_lower = question.lower()

        # Step 1: Classify intent type
        intent_type = self._classify_intent(question_lower)

        # Step 2: Extract metrics
        metrics = self._extract_metrics(question_lower)

        # Step 3: Extract dimensions
        dimensions = self._extract_dimensions(question_lower)

        # Step 4: Extract entities (stores, customers, products)
        entities = self._extract_entities(question_lower)

        # Step 5: Extract time periods
        primary_start, primary_end, compare_start, compare_end = self._extract_time_periods(question)

        # Step 6: Extract granularity
        granularity = self._extract_granularity(question_lower)

        # Step 7: Extract filters
        filters = self._extract_filters(question_lower)

        # Step 8: Check for ambiguities
        ambiguities = self._check_ambiguities(question_lower, metrics, dimensions)

        # Step 9: Determine if NL2SQL is required
        requires_nl2sql = self._requires_nl2sql(intent_type, metrics, question_lower)

        # Step 10: Check if clarification is needed
        requires_clarification, clarification_questions = self._check_clarification(
            ambiguities, metrics, primary_start
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            intent_type, metrics, dimensions, primary_start, requires_clarification
        )

        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            primary_metrics=metrics.get("primary", []),
            secondary_metrics=metrics.get("secondary", []),
            dimensions=dimensions,
            filters=filters,
            entities=entities,
            primary_period_start=primary_start,
            primary_period_end=primary_end,
            comparison_period_start=compare_start,
            comparison_period_end=compare_end,
            granularity=granularity,
            requires_nl2sql=requires_nl2sql,
            ambiguities=ambiguities,
            requires_clarification=requires_clarification,
            clarification_questions=clarification_questions,
            raw_components={
                "question": question,
                "question_lower": question_lower,
                "has_comparison": compare_start is not None,
                "has_trend": "trend" in question_lower or "over time" in question_lower,
            },
        )

    def _classify_intent(self, question: str) -> IntentType:
        """Classify the primary intent of the question."""
        scores: dict[IntentType, float] = {intent: 0.0 for intent in IntentType}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question:
                    scores[intent] += 1.0

        # Boost specific patterns
        if "why" in question:
            scores[IntentType.ATTRIBUTION] += 2.0
        if "why did" in question or "what caused" in question:
            scores[IntentType.ATTRIBUTION] += 3.0
        if "contribute" in question or "driver" in question:
            scores[IntentType.CONTRIBUTION] += 2.0
        if self.TIME_PATTERNS["yoy"].search(question):
            scores[IntentType.COMPARISON] += 2.0

        # Return highest scoring intent
        best_intent = max(scores, key=scores.get)
        if scores[best_intent] == 0:
            return IntentType.METRIC_QUERY
        return best_intent

    def _extract_metrics(self, question: str) -> dict[str, list[str]]:
        """Extract primary and secondary metrics from question."""
        primary: list[str] = []
        secondary: list[str] = []

        # Check against known metric keywords
        for metric_id, keywords in self.METRIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question:
                    if metric_id not in primary:
                        primary.append(metric_id)
                    break

        # Check semantic package if available
        if self.semantic_package:
            for metric in self.semantic_package.metrics:
                metric_label_lower = metric.label.lower()
                if metric_label_lower in question and metric.id not in primary:
                    primary.append(metric.id)

        # Infer secondary metrics based on primary
        if "revenue" in primary or "sales" in str(primary):
            if "profit" in question:
                secondary.append("gross_profit")
            if "volume" in question or "quantity" in question:
                secondary.append("order_count")
            if "price" in question:
                secondary.append("average_order_value")

        return {"primary": primary, "secondary": secondary}

    def _extract_dimensions(self, question: str) -> list[str]:
        """Extract dimensions for grouping/filtering."""
        dimensions: list[str] = []

        for dim_id, keywords in self.DIMENSION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question:
                    if dim_id not in dimensions:
                        dimensions.append(dim_id)
                    break

        # Infer dimension from context
        if "by" in question:
            match = re.search(r"by\s+(\w+)", question)
            if match:
                dim = match.group(1).lower()
                if dim not in dimensions:
                    dimensions.append(dim)

        return dimensions

    def _extract_entities(self, question: str) -> list[str]:
        """Extract specific entities mentioned in question."""
        entities: list[str] = []

        # Look for quoted strings (likely entity names)
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', question)
        for match in quoted:
            entity = match[0] or match[1]
            if entity:
                entities.append(entity.strip())

        # Look for pattern "in/for [Entity Name]"
        location_patterns = [
            r"(?:in|for|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"(?:store|location)\s+([A-Z0-9-]+)",
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, question)
            entities.extend(matches)

        return entities

    def _extract_time_periods(
        self, question: str
    ) -> tuple[date | None, date | None, date | None, date | None]:
        """Extract primary and comparison time periods."""
        from calendar import monthrange
        from datetime import date, timedelta

        today = date.today()
        primary_start: date | None = None
        primary_end: date | None = None
        compare_start: date | None = None
        compare_end: date | None = None

        # Try explicit month + year
        match = self.TIME_PATTERNS["month_year"].search(question)
        if match:
            month_name, year_str = match.groups()
            month_map = {
                "january": 1, "february": 2, "march": 3, "april": 4,
                "may": 5, "june": 6, "july": 7, "august": 8,
                "september": 9, "october": 10, "november": 11, "december": 12,
            }
            month = month_map[month_name.lower()]
            year = int(year_str)
            _, last_day = monthrange(year, month)
            primary_start = date(year, month, 1)
            primary_end = date(year, month, last_day)

            # Check for YoY comparison
            if self.TIME_PATTERNS["yoy"].search(question):
                compare_start = date(year - 1, month, 1)
                compare_end = date(year - 1, month, last_day)
            else:
                # Default to previous period
                compare_month = month - 1 if month > 1 else 12
                compare_year = year if month > 1 else year - 1
                _, last_day = monthrange(compare_year, compare_month)
                compare_start = date(compare_year, compare_month, 1)
                compare_end = date(compare_year, compare_month, last_day)
            return primary_start, primary_end, compare_start, compare_end

        # Try relative periods
        relative_match = self.TIME_PATTERNS["relative"].search(question)
        if relative_match:
            qualifier, period = relative_match.groups()
            qualifier = qualifier.lower()
            period = period.lower().strip()

            if period in ("month", "this month", "current month"):
                primary_start = date(today.year, today.month, 1)
                _, last_day = monthrange(today.year, today.month)
                primary_end = date(today.year, today.month, last_day)
                if qualifier in ("last", "previous"):
                    prev_month = today.month - 1 if today.month > 1 else 12
                    prev_year = today.year if today.month > 1 else today.year - 1
                    _, last_day = monthrange(prev_year, prev_month)
                    compare_start = date(prev_year, prev_month, 1)
                    compare_end = date(prev_year, prev_month, last_day)

            elif period in ("quarter", "this quarter", "current quarter"):
                current_quarter = (today.month - 1) // 3 + 1
                q_start_month = (current_quarter - 1) * 3 + 1
                primary_start = date(today.year, q_start_month, 1)
                if current_quarter == 4:
                    primary_end = date(today.year, 12, 31)
                else:
                    _, last_day = monthrange(today.year, q_start_month + 3)
                    primary_end = date(today.year, q_start_month + 3, last_day)

            elif period in ("year", "this year", "current year"):
                primary_start = date(today.year, 1, 1)
                primary_end = date(today.year, 12, 31)

            elif period in ("week", "this week", "current week"):
                # Approximate week start
                days_since_monday = today.weekday()
                primary_start = today - timedelta(days=days_since_monday)
                primary_end = primary_start + timedelta(days=6)

        return primary_start, primary_end, compare_start, compare_end

    def _extract_granularity(self, question: str) -> str | None:
        """Extract time granularity if specified."""
        granularities = {
            "daily": ["daily", "day by day", "per day"],
            "weekly": ["weekly", "week by week", "per week"],
            "monthly": ["monthly", "month by month", "per month"],
            "quarterly": ["quarterly", "quarter by quarter", "per quarter"],
            "yearly": ["yearly", "annually", "per year"],
        }

        for granularity, patterns in granularities.items():
            for pattern in patterns:
                if pattern in question:
                    return granularity
        return None

    def _extract_filters(self, question: str) -> dict[str, list[str]]:
        """Extract dimension filters from question."""
        filters: dict[str, list[str]] = {}

        # Region filter
        region_match = re.search(
            r"(?:in|for)\s+(north|south|east|west|china|华北|华东|华南|华中)",
            question,
            re.I,
        )
        if region_match:
            filters.setdefault("region", []).append(region_match.group(1))

        # Store filter
        store_match = re.search(r"store\s+([A-Za-z0-9\s-]+?)(?:\s|$|,)", question, re.I)
        if store_match:
            filters.setdefault("store", []).append(store_match.group(1).strip())

        # Product filter
        product_match = re.search(
            r"(?:product|category)\s+([A-Za-z0-9\s-]+?)(?:\s|$|,)", question, re.I
        )
        if product_match:
            filters.setdefault("product", []).append(product_match.group(1).strip())

        return filters

    def _check_ambiguities(
        self, question: str, metrics: dict[str, list[str]], dimensions: list[str]
    ) -> list[str]:
        """Check for ambiguous elements that need resolution."""
        ambiguities: list[str] = []

        if not metrics["primary"]:
            ambiguities.append("No clear metric identified in question")

        if not dimensions and ("break down" in question or "by" in question):
            ambiguities.append("Breakdown requested but no dimension specified")

        # Check for profit-related queries on data that might not have cost
        if any(m in ["profit", "net_income", "gross_profit"] for m in metrics.get("primary", [])):
            ambiguities.append("Profit metric requested - verify cost data availability")

        return ambiguities

    def _requires_nl2sql(
        self, intent: IntentType, metrics: dict[str, list[str]], question: str
    ) -> bool:
        """Determine if NL2SQL path is required vs semantic query."""
        # NL2SQL is required for:
        # 1. Attribution analysis (why questions)
        # 2. Complex filters not in semantic layer
        # 3. Ad-hoc queries with unknown metrics
        # 4. When semantic layer doesn't have the metric

        if intent == IntentType.ATTRIBUTION:
            return True

        if intent == IntentType.drilldown and not metrics["primary"]:
            return True

        return bool("custom" in question or "specific" in question)

    def _check_clarification(
        self, ambiguities: list[str], metrics: dict[str, list[str]], period_start: date | None
    ) -> tuple[bool, list[str]]:
        """Check if clarification is needed and generate questions."""
        questions: list[str] = []

        if not metrics["primary"] and not ambiguities:
            questions.append(
                "Which metric would you like to analyze? "
                "For example: revenue, orders, profit, or customer count."
            )

        if not period_start:
            questions.append(
                "Which time period are you interested in? "
                "For example: this month, last quarter, or year to date."
            )

        return len(questions) > 0, questions

    def _calculate_confidence(
        self,
        intent: IntentType,
        metrics: dict[str, list[str]],
        dimensions: list[str],
        period: date | None,
        needs_clarification: bool,
    ) -> float:
        """Calculate confidence score for the resolved intent."""
        confidence = 0.5  # Base confidence

        if metrics["primary"]:
            confidence += 0.2

        if dimensions:
            confidence += 0.1

        if period:
            confidence += 0.15

        if intent != IntentType.UNKNOWN:
            confidence += 0.1

        if not needs_clarification:
            confidence += 0.05

        return min(confidence, 1.0)
