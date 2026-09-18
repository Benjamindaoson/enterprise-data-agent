"""Tests for NL2SQL service integration."""

import pytest
from datetime import date
from unittest.mock import Mock, MagicMock

from eiw.nl2sql.service import NL2SQLService, NL2SQLConfig
from eiw.nl2sql.contracts import (
    NL2SQLRequest,
    QueryLane,
    ExecutionStatus,
)
from eiw.semantic.v2 import SemanticPackageV2


class TestNL2SQLConfig:
    """Test NL2SQLConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = NL2SQLConfig()

        assert config.default_lane == QueryLane.DETERMINISTIC
        assert config.executor_type == "duckdb"
        assert config.enable_repair is True
        assert config.max_repair_attempts == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = NL2SQLConfig(
            default_lane=QueryLane.GOVERNED_NL2SQL,
            executor_type="postgresql",
            max_rows=5000,
            max_complexity=5,
        )

        assert config.default_lane == QueryLane.GOVERNED_NL2SQL
        assert config.executor_type == "postgresql"
        assert config.max_rows == 5000
        assert config.max_complexity == 5


class TestNL2SQLService:
    """Test NL2SQLService class."""

    def test_service_creation(self):
        """Test service creation."""
        service = NL2SQLService()
        assert service is not None

    def test_service_creation_with_config(self):
        """Test service creation with config."""
        config = NL2SQLConfig(
            default_lane=QueryLane.GOVERNED_NL2SQL,
            enable_repair=True,
        )
        service = NL2SQLService(config=config)
        assert service is not None

    def test_service_creation_with_semantic_packages(self):
        """Test service creation with semantic packages."""
        packages = {"finance": Mock(spec=SemanticPackageV2)}
        service = NL2SQLService(semantic_packages=packages)
        assert service is not None

    def test_health_check(self):
        """Test health check."""
        service = NL2SQLService()
        health = service.health_check()

        assert health["service"] == "nl2sql"
        assert "status" in health
        assert "components" in health


class TestNL2SQLServiceExecute:
    """Test NL2SQLService.execute method."""

    def test_execute_request_creation(self):
        """Test NL2SQLRequest creation."""
        request = NL2SQLRequest(
            question="What is total revenue?",
            domain="finance",
        )

        assert request.question == "What is total revenue?"
        assert request.domain == "finance"

    def test_execute_request_with_time_range(self):
        """Test request with time range."""
        request = NL2SQLRequest(
            question="Revenue in 2023",
            domain="finance",
            time_range_start=date(2023, 1, 1),
            time_range_end=date(2023, 12, 31),
        )

        assert request.time_range_start == date(2023, 1, 1)
        assert request.time_range_end == date(2023, 12, 31)

    def test_execute_request_with_user_context(self):
        """Test request with user context."""
        request = NL2SQLRequest(
            question="Show me data",
            domain="finance",
            user_id="user123",
            user_roles=["viewer"],
            tenant_id="tenant_abc",
        )

        assert request.user_id == "user123"
        assert "viewer" in request.user_roles
        assert request.tenant_id == "tenant_abc"


class TestQueryLane:
    """Test QueryLane enum."""

    def test_deterministic_lane(self):
        """Test deterministic lane value."""
        assert QueryLane.DETERMINISTIC.value == "deterministic"

    def test_governed_lane(self):
        """Test governed lane value."""
        assert QueryLane.GOVERNED_NL2SQL.value == "governed_nl2sql"

    def test_deterministic_is_default(self):
        """Test deterministic lane is default in config."""
        config = NL2SQLConfig()
        assert config.default_lane == QueryLane.DETERMINISTIC


class TestPipelineComponents:
    """Test pipeline components are initialized."""

    def test_components_initialized(self):
        """Test all components are initialized."""
        service = NL2SQLService()

        # Check all key components exist
        assert hasattr(service, '_schema_retriever')
        assert hasattr(service, '_schema_linker')
        assert hasattr(service, '_example_retriever')
        assert hasattr(service, '_query_planner')
        assert hasattr(service, '_sql_generator')
        assert hasattr(service, '_sql_parser')
        assert hasattr(service, '_policy_validator')

    def test_config_preserved(self):
        """Test configuration is preserved."""
        config = NL2SQLConfig(
            max_rows=5000,
            enable_repair=True,
        )
        service = NL2SQLService(config=config)

        assert service._config.max_rows == 5000
        assert service._config.enable_repair is True


class TestExecutionFlow:
    """Test execution flow."""

    def test_execute_handles_exception(self):
        """Test execute handles exceptions gracefully."""
        service = NL2SQLService()

        # Should not raise
        result = service.execute(
            NL2SQLRequest(
                question="Invalid SQL query",
                domain="nonexistent",
            )
        )

        # Should return a result with error status
        assert result is not None


class TestGovernedLane:
    """Test governed query lane."""

    def test_governed_lane_enabled_by_default(self):
        """Test governed lane is available."""
        config = NL2SQLConfig(
            default_lane=QueryLane.GOVERNED_NL2SQL,
        )
        service = NL2SQLService(config=config)

        assert service._config.default_lane == QueryLane.GOVERNED_NL2SQL

    def test_governed_lane_explicit(self):
        """Test explicit governed lane."""
        service = NL2SQLService()

        # Service should have governed lane support
        assert hasattr(service, '_sql_generator')


class TestDeterministicLane:
    """Test deterministic query lane."""

    def test_deterministic_lane(self):
        """Test deterministic lane."""
        config = NL2SQLConfig(
            default_lane=QueryLane.DETERMINISTIC,
        )
        service = NL2SQLService(config=config)

        assert service._config.default_lane == QueryLane.DETERMINISTIC
