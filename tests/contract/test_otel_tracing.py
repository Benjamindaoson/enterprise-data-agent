"""Tests for OpenTelemetry tracing implementation."""

from __future__ import annotations

import pytest

from eiw.observability import (
    OTelConfig,
    filter_sensitive_fields,
    SENSITIVE_FIELDS,
)


class TestOTelConfig:
    """Test OTel configuration."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = OTelConfig()
        assert config.service_name == "enterprise-data-agent"
        assert config.enabled is True
        assert config.otlp_endpoint is None  # None = in-memory only

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = OTelConfig(
            service_name="test-service",
            otlp_endpoint="http://collector:4317",
            environment="production",
        )
        assert config.service_name == "test-service"
        assert config.otlp_endpoint == "http://collector:4317"
        assert config.environment == "production"


class TestSensitiveFieldFiltering:
    """Test sensitive field filtering."""

    def test_password_filtered(self) -> None:
        """Test that password fields are filtered."""
        data = {"username": "admin", "password": "secret123"}
        filtered = filter_sensitive_fields(data)
        assert filtered["password"] == "[REDACTED]"
        assert filtered["username"] == "admin"

    def test_secret_filtered(self) -> None:
        """Test that secret fields are filtered."""
        data = {"api_key": "sk-secret-key", "token": "bearer-token-123"}
        filtered = filter_sensitive_fields(data)
        assert filtered["api_key"] == "[REDACTED]"
        assert filtered["token"] == "[REDACTED]"

    def test_chain_of_thought_filtered(self) -> None:
        """Test that chain_of_thought is filtered."""
        data = {"query": "Calculate revenue", "chain_of_thought": "Step 1: Get data"}
        filtered = filter_sensitive_fields(data)
        assert filtered["chain_of_thought"] == "[REDACTED]"
        assert filtered["query"] == "Calculate revenue"

    def test_sensitive_fields_constant(self) -> None:
        """Test SENSITIVE_FIELDS constant includes expected fields."""
        assert "password" in SENSITIVE_FIELDS
        assert "secret" in SENSITIVE_FIELDS
        assert "token" in SENSITIVE_FIELDS
        assert "api_key" in SENSITIVE_FIELDS


class TestStructuredLoggingFormats:
    """Test structured logging basics."""

    def test_json_formatter_produces_output(self) -> None:
        """Test that JSON formatter produces output."""
        import json
        from io import StringIO
        import logging
        from eiw.observability.logging import StructuredJsonFormatter

        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Test message"
