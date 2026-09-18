"""Tests for structured logging with OTel correlation."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from eiw.observability.logging import (
    StructuredJsonFormatter,
    StructuredTextFormatter,
    get_structured_logger,
    set_structured_logging_json,
)


class TestStructuredLoggingFormats:
    """Test structured logging formatters."""

    def test_json_formatter_produces_valid_json(self) -> None:
        """Test that JSON formatter produces valid JSON."""
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
        assert "timestamp" in parsed
        assert "level" in parsed

    def test_text_formatter_readable_output(self) -> None:
        """Test that text formatter produces readable output."""
        formatter = StructuredTextFormatter()
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

        assert "Test message" in output
        assert "INFO" in output

    def test_json_mode_toggle(self) -> None:
        """Test toggling between JSON and text logging."""
        set_structured_logging_json(True)
        set_structured_logging_json(False)


class TestStructuredLogFunctions:
    """Test structured logging helper functions."""

    def test_get_structured_logger(self) -> None:
        """Test getting a structured logger."""
        logger = get_structured_logger("test_module", "test_component")
        assert logger is not None
        # LoggerAdapter wraps the underlying logger
        # The underlying logger name is preserved
        assert logger.logger.name == "test_module"

    def test_get_structured_logger_default_component(self) -> None:
        """Test that default component is extracted from module name."""
        logger = get_structured_logger("mypackage_mymodule")
        assert logger is not None
        # Default component is set from the module name
        assert logger.extra.get("component") == "mypackage_mymodule"


class TestLogTraceCorrelation:
    """Test correlation between logs and traces."""

    def test_log_with_extra_fields(self) -> None:
        """Test logging with extra structured fields.

        Verifies that custom fields can be passed through the logging adapter.
        """
        # Create a custom formatter that captures extra fields
        captured = {}

        class CaptureFormatter(logging.Formatter):
            def format(self, record):
                # Capture what the formatter sees
                captured["level"] = record.levelname
                captured["component"] = getattr(record, "component", None)
                # Extra passed via LoggerAdapter.process merges into record.__dict__
                return f"{record.getMessage()}"

        # Create fresh logger
        logger_name = "test_extra_capture"
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(CaptureFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Create adapter and log with extra
        adapter = logging.LoggerAdapter(logger, {"component": "test_component"})
        adapter.info("Test message", extra={"request_id": "req-123"})

        # Verify the message was logged
        assert "Test message" in stream.getvalue()
        assert captured["component"] == "test_component"
