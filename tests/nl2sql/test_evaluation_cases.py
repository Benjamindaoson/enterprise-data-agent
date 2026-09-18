"""Tests for NL2SQL evaluation cases."""

import pytest

from eiw.nl2sql.evaluation_cases import (
    EvaluationCase,
    CaseCategory,
    ExpectedOutcome,
    ALL_EVALUATION_CASES,
    SUCCESS_CASES,
    SYNTAX_ERROR_CASES,
    POLICY_VIOLATION_CASES,
    SEMANTIC_ERROR_CASES,
    EXECUTION_ERROR_CASES,
    SECURITY_BYPASS_CASES,
    EDGE_CASES,
    COMPLEXITY_CASES,
    get_cases_by_category,
    get_case_by_id,
    get_cases_by_domain,
    get_cases_by_outcome,
    get_case_count,
    get_case_summary,
)


class TestCaseCategories:
    """Test case categories."""

    def test_all_categories_present(self):
        """Test all expected categories are present."""
        categories = {c.category for c in ALL_EVALUATION_CASES}
        expected = {
            CaseCategory.SUCCESS,
            CaseCategory.SYNTAX_ERROR,
            CaseCategory.POLICY_VIOLATION,
            CaseCategory.SEMANTIC_ERROR,
            CaseCategory.EXECUTION_ERROR,
            CaseCategory.SECURITY_BYPASS,
            CaseCategory.EDGE_CASE,
            CaseCategory.COMPLEXITY_EXCEEDED,
        }
        assert categories == expected

    def test_success_cases(self):
        """Test success cases exist."""
        assert len(SUCCESS_CASES) >= 25
        for case in SUCCESS_CASES:
            assert case.expected_outcome == ExpectedOutcome.SUCCESS

    def test_syntax_error_cases(self):
        """Test syntax error cases exist."""
        assert len(SYNTAX_ERROR_CASES) >= 10
        for case in SYNTAX_ERROR_CASES:
            assert case.category == CaseCategory.SYNTAX_ERROR

    def test_policy_violation_cases(self):
        """Test policy violation cases exist."""
        assert len(POLICY_VIOLATION_CASES) >= 10
        for case in POLICY_VIOLATION_CASES:
            assert case.category == CaseCategory.POLICY_VIOLATION

    def test_semantic_error_cases(self):
        """Test semantic error cases exist."""
        assert len(SEMANTIC_ERROR_CASES) >= 10
        for case in SEMANTIC_ERROR_CASES:
            assert case.category == CaseCategory.SEMANTIC_ERROR

    def test_execution_error_cases(self):
        """Test execution error cases exist."""
        assert len(EXECUTION_ERROR_CASES) >= 8
        for case in EXECUTION_ERROR_CASES:
            assert case.category == CaseCategory.EXECUTION_ERROR

    def test_security_bypass_cases(self):
        """Test security bypass cases exist."""
        assert len(SECURITY_BYPASS_CASES) >= 8
        for case in SECURITY_BYPASS_CASES:
            assert case.category == CaseCategory.SECURITY_BYPASS

    def test_edge_cases(self):
        """Test edge cases exist."""
        assert len(EDGE_CASES) >= 12
        for case in EDGE_CASES:
            assert case.category == CaseCategory.EDGE_CASE

    def test_complexity_cases(self):
        """Test complexity exceeded cases exist."""
        assert len(COMPLEXITY_CASES) >= 8
        for case in COMPLEXITY_CASES:
            assert case.category == CaseCategory.COMPLEXITY_EXCEEDED


class TestTotalCaseCount:
    """Test total case count."""

    def test_total_cases_over_100(self):
        """Test total cases exceed 100."""
        count = get_case_count()
        assert count >= 100, f"Expected at least 100 cases, got {count}"

    def test_case_summary(self):
        """Test case summary contains all categories."""
        summary = get_case_summary()
        expected_categories = {
            "success",
            "syntax_error",
            "policy_violation",
            "semantic_error",
            "execution_error",
            "security_bypass",
            "edge_case",
            "complexity_exceeded",
        }
        assert set(summary.keys()) == expected_categories


class TestGetCasesByCategory:
    """Test filtering cases by category."""

    def test_get_success_cases(self):
        """Test getting success cases."""
        cases = get_cases_by_category(CaseCategory.SUCCESS)
        assert len(cases) == len(SUCCESS_CASES)
        for case in cases:
            assert case.category == CaseCategory.SUCCESS

    def test_get_policy_violation_cases(self):
        """Test getting policy violation cases."""
        cases = get_cases_by_category(CaseCategory.POLICY_VIOLATION)
        assert len(cases) == len(POLICY_VIOLATION_CASES)

    def test_get_security_bypass_cases(self):
        """Test getting security bypass cases."""
        cases = get_cases_by_category(CaseCategory.SECURITY_BYPASS)
        assert len(cases) == len(SECURITY_BYPASS_CASES)


class TestGetCaseById:
    """Test getting case by ID."""

    def test_get_existing_case(self):
        """Test getting existing case."""
        case = get_case_by_id("nl2sql-001")
        assert case is not None
        assert case.case_id == "nl2sql-001"

    def test_get_nonexistent_case(self):
        """Test getting nonexistent case."""
        case = get_case_by_id("nl2sql-999")
        assert case is None


class TestGetCasesByDomain:
    """Test filtering cases by domain."""

    def test_get_finance_cases(self):
        """Test getting finance domain cases."""
        cases = get_cases_by_domain("finance")
        assert len(cases) > 0
        for case in cases:
            assert case.domain == "finance"

    def test_get_sales_operations_cases(self):
        """Test getting sales_operations domain cases."""
        cases = get_cases_by_domain("sales_operations")
        assert len(cases) > 0
        for case in cases:
            assert case.domain == "sales_operations"

    def test_get_supply_chain_cases(self):
        """Test getting supply_chain domain cases."""
        cases = get_cases_by_domain("supply_chain")
        assert len(cases) > 0
        for case in cases:
            assert case.domain == "supply_chain"


class TestGetCasesByOutcome:
    """Test filtering cases by expected outcome."""

    def test_get_success_outcome_cases(self):
        """Test getting cases with success outcome."""
        cases = get_cases_by_outcome(ExpectedOutcome.SUCCESS)
        assert len(cases) > 0
        for case in cases:
            assert case.expected_outcome == ExpectedOutcome.SUCCESS

    def test_get_error_outcome_cases(self):
        """Test getting cases with error outcome."""
        cases = get_cases_by_outcome(ExpectedOutcome.ERROR)
        assert len(cases) > 0
        for case in cases:
            assert case.expected_outcome == ExpectedOutcome.ERROR

    def test_get_rejected_outcome_cases(self):
        """Test getting cases with rejected outcome."""
        cases = get_cases_by_outcome(ExpectedOutcome.REJECTED)
        assert len(cases) > 0
        for case in cases:
            assert case.expected_outcome == ExpectedOutcome.REJECTED


class TestCaseProperties:
    """Test evaluation case properties."""

    def test_cases_have_required_fields(self):
        """Test all cases have required fields."""
        for case in ALL_EVALUATION_CASES:
            assert case.case_id is not None
            assert case.category is not None
            assert case.description is not None
            assert case.question is not None
            assert case.domain is not None
            assert case.expected_outcome is not None

    def test_case_ids_unique(self):
        """Test case IDs are unique."""
        case_ids = [c.case_id for c in ALL_EVALUATION_CASES]
        assert len(case_ids) == len(set(case_ids))

    def test_case_ids_follow_pattern(self):
        """Test case IDs follow nl2sql-XXX pattern."""
        for case in ALL_EVALUATION_CASES:
            assert case.case_id.startswith("nl2sql-")
            assert case.case_id[7:].isdigit()

    def test_success_cases_have_sql_pattern(self):
        """Test success cases have expected SQL patterns (if defined)."""
        for case in SUCCESS_CASES:
            if case.expected_outcome == ExpectedOutcome.SUCCESS:
                # SQL pattern is optional, but if defined should not be empty
                if case.expected_sql_pattern is not None:
                    assert len(case.expected_sql_pattern) > 0


class TestCaseToDict:
    """Test case to_dict conversion."""

    def test_to_dict_contains_all_fields(self):
        """Test to_dict contains all expected fields."""
        case = ALL_EVALUATION_CASES[0]
        d = case.to_dict()

        assert "case_id" in d
        assert "category" in d
        assert "description" in d
        assert "question" in d
        assert "domain" in d
        assert "expected_outcome" in d

    def test_to_dict_values_are_serializable(self):
        """Test to_dict values are JSON serializable."""
        for case in ALL_EVALUATION_CASES:
            d = case.to_dict()
            # Should not raise
            import json
            json.dumps(d)


class TestCaseDistribution:
    """Test case distribution across categories."""

    def test_diverse_outcomes(self):
        """Test cases have diverse expected outcomes."""
        outcomes = {c.expected_outcome for c in ALL_EVALUATION_CASES}
        # Should have at least 3 different outcome types
        assert len(outcomes) >= 3

    def test_diverse_domains(self):
        """Test cases cover multiple domains."""
        domains = {c.domain for c in ALL_EVALUATION_CASES}
        # Should cover at least 3 domains
        assert len(domains) >= 3

    def test_each_category_has_minimum_cases(self):
        """Test each category has minimum required cases."""
        summary = get_case_summary()

        assert summary.get("success", 0) >= 20
        assert summary.get("syntax_error", 0) >= 10
        assert summary.get("policy_violation", 0) >= 10
        assert summary.get("semantic_error", 0) >= 10
        assert summary.get("security_bypass", 0) >= 8


class TestSecurityBypassCases:
    """Test security bypass cases specifically."""

    def test_bypass_cases_have_expected_errors(self):
        """Test security bypass cases expect security errors."""
        for case in SECURITY_BYPASS_CASES:
            assert case.expected_error in [
                "SECURITY_POLICY",
                "POLICY_VIOLATION",
            ]

    def test_bypass_cases_have_policy_checks(self):
        """Test security bypass cases have policy check info."""
        for case in SECURITY_BYPASS_CASES:
            assert case.expected_policy_check is not None

    def test_bypass_cases_cover_common_techniques(self):
        """Test security bypass cases cover common techniques."""
        techniques = [c.description.lower() for c in SECURITY_BYPASS_CASES]
        assert any("comment" in t for t in techniques)
        assert any("union" in t for t in techniques)
        assert any("injection" in t for t in techniques)
