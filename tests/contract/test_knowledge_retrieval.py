"""Tests for Knowledge Base and RAG retrieval functionality."""

from __future__ import annotations

import pytest

from eiw.knowledge import (
    KnowledgeBase,
    KnowledgeItem,
    KnowledgeRetrievalQuery,
    KnowledgeRetrievalResult,
    KnowledgeSourceType,
    PermissionLevel,
)


class TestKnowledgeBaseBasics:
    """Test basic knowledge base operations."""

    def test_knowledge_base_exists(self) -> None:
        """Test that KnowledgeBase can be instantiated."""
        kb = KnowledgeBase()
        assert kb is not None

    def test_permission_levels_exist(self) -> None:
        """Test that permission levels are defined."""
        assert PermissionLevel.PUBLIC is not None
        assert PermissionLevel.INTERNAL is not None
        assert PermissionLevel.CONFIDENTIAL is not None
        assert PermissionLevel.RESTRICTED is not None

    def test_source_types_exist(self) -> None:
        """Test that source types are defined."""
        assert KnowledgeSourceType.METRIC_DEFINITION is not None
        assert KnowledgeSourceType.BUSINESS_GLOSSARY is not None
        assert KnowledgeSourceType.SQL_EXAMPLE is not None
        assert KnowledgeSourceType.TABLE_DOCUMENTATION is not None


class TestKnowledgeRetrievalResult:
    """Test knowledge retrieval result."""

    def test_result_has_items(self) -> None:
        """Test that result has items list."""
        result = KnowledgeRetrievalResult(items=[], query_text="test")
        assert isinstance(result.items, list)
        assert result.total_found == 0
