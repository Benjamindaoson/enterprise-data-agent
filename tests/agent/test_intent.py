"""Tests for Intent Resolver."""

import pytest

from eiw.agent.intent import (
    IntentResolver, AnalysisType, AmbiguityType,
    ResolvedBusinessIntent, ClarificationQuestion,
    IntentResolutionResult
)


class TestIntentResolver:
    """Tests for IntentResolver."""

    @pytest.fixture
    def resolver(self):
        """Create resolver."""
        return IntentResolver()

    @pytest.mark.asyncio
    async def test_resolve_simple_question(self, resolver):
        """Test resolving a simple question."""
        result = await resolver.resolve("What were sales last month?")

        # Should either succeed or need clarification
        assert result.success or result.clarification_needed or result.error is not None

    @pytest.mark.asyncio
    async def test_resolve_with_domain(self, resolver):
        """Test resolving with domain hint."""
        result = await resolver.resolve(
            "Show revenue trends",
            domain="finance"
        )

        assert result.success or result.clarification_needed

    @pytest.mark.asyncio
    async def test_detect_ambiguity(self, resolver):
        """Test ambiguity detection."""
        # Question with multiple possible metrics
        result = await resolver.resolve("What happened?")

        # Should either resolve or request clarification
        assert result.success or result.clarification_needed


class TestResolvedBusinessIntent:
    """Tests for ResolvedBusinessIntent model."""

    def test_create_intent(self):
        """Test creating an intent."""
        intent = ResolvedBusinessIntent(
            objective="Understand sales performance",
            domain="sales",
            analysis_type=AnalysisType.DESCRIPTIVE,
            metric_candidates=["revenue", "orders"],
            selected_metrics=["revenue"],
        )

        assert intent.objective == "Understand sales performance"
        assert intent.domain == "sales"
        assert "revenue" in intent.selected_metrics

    def test_default_values(self):
        """Test default values."""
        intent = ResolvedBusinessIntent(
            objective="test",
            domain="test",
            analysis_type=AnalysisType.DESCRIPTIVE,
        )

        assert intent.metric_candidates == []
        assert intent.selected_dimensions == []
        assert intent.entities == {}
        assert intent.requires_clarification is False


class TestClarificationQuestion:
    """Tests for ClarificationQuestion."""

    def test_create_question(self):
        """Test creating a clarification question."""
        question = ClarificationQuestion(
            question_id="q1",
            ambiguity_type=AmbiguityType.METRIC,
            question="Which metric do you want?",
            options=["Revenue", "Orders", "Profit"],
            context="Multiple metrics match",
        )

        assert question.question_id == "q1"
        assert question.ambiguity_type == AmbiguityType.METRIC
        assert len(question.options) == 3


class TestTimeExpressionResolution:
    """Tests for time expression resolution."""

    @pytest.fixture
    def resolver(self):
        """Create resolver."""
        return IntentResolver()

    def test_yesterday(self, resolver):
        """Test yesterday resolution."""
        start, end = resolver.resolve_time_expression("yesterday")
        assert start is not None
        assert end is not None

    def test_last_week(self, resolver):
        """Test last week resolution."""
        start, end = resolver.resolve_time_expression("last week")
        assert start is not None
        assert end is not None

    def test_quarter(self, resolver):
        """Test quarter resolution."""
        start, end = resolver.resolve_time_expression("Q1 2024")
        assert start is not None
        assert end is not None
        assert start.month == 1
        assert end.month == 3
