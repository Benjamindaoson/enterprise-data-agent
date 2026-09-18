"""NL2SQL - Natural Language to SQL conversion with governance.

This package provides:
- Full NL2SQL pipeline orchestration
- Permission-aware schema retrieval
- SQLGlot AST validation
- Comprehensive security policies
- Semantic validation
- Cost guards and query analysis
- Result validation
- Bounded SQL repair loop
- Dual query lanes (deterministic vs governed)
- OpenTelemetry tracing
"""

from __future__ import annotations

# Core contracts
from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    QueryLane,
    ExecutionStatus,
    TableInfo,
    ColumnInfo,
    JoinInfo,
    SchemaContext,
    NL2SQLRequest,
    LogicalQueryPlan,
    GeneratedSQL,
    SQLValidationResult,
    ExecutionResult,
    RepairAttempt,
    ResultValidationResult,
    NL2SQLResult,
    SQLGeneratorProvider,
    ExecutorProvider,
)

# Schema retrieval
from eiw.nl2sql.schema_retriever import SchemaRetriever

# Schema linking
from eiw.nl2sql.schema_linker import SchemaLinker, SchemaLinkingResult

# Example retrieval
from eiw.nl2sql.example_retriever import ExampleRetriever, SQLExample

# Query planning
from eiw.nl2sql.planner import QueryPlanner

# SQL generation
from eiw.nl2sql.generator import (
    MockSQLGenerator,
    LLMSQLGenerator,
    create_sql_generator,
)

# SQL parsing
from eiw.nl2sql.parser import SQLParser, ParsedSQL

# Policy validation
from eiw.nl2sql.policy import (
    SQLPolicyValidator,
    PolicyContext,
    check_sql_security_bypass_attempts,
)

# Semantic validation
from eiw.nl2sql.semantic_validator import SemanticValidator, MetricFormulaCheck

# Join validation
from eiw.nl2sql.join_validator import JoinValidator, JoinValidationError

# Cost guard
from eiw.nl2sql.cost_guard import CostGuard, CostEstimate, CostThreshold

# SQL execution
from eiw.nl2sql.executor import (
    DuckDBExecutor,
    PostgreSQLExecutor,
    ExecutionConfig,
    create_executor,
)

# Result validation
from eiw.nl2sql.result_validator import (
    ResultValidator,
    ColumnValidation,
    ResultValidationConfig,
)

# SQL repair
from eiw.nl2sql.repair import (
    SQLRepair,
    RepairConfig,
    RepairContext,
    RepairStrategy,
    RepairClassification,
    create_repair,
)

# Service orchestration
from eiw.nl2sql.service import NL2SQLService, NL2SQLConfig, create_nl2sql_service


__all__ = [
    # Contracts
    "SQLValidationErrorCategory",
    "QueryLane",
    "ExecutionStatus",
    "TableInfo",
    "ColumnInfo",
    "JoinInfo",
    "SchemaContext",
    "NL2SQLRequest",
    "LogicalQueryPlan",
    "GeneratedSQL",
    "SQLValidationResult",
    "ExecutionResult",
    "RepairAttempt",
    "ResultValidationResult",
    "NL2SQLResult",
    "SQLGeneratorProvider",
    "ExecutorProvider",
    # Schema retrieval
    "SchemaRetriever",
    # Schema linking
    "SchemaLinker",
    "SchemaLinkingResult",
    "BusinessConcept",
    "SchemaLink",
    # Example retrieval
    "ExampleRetriever",
    "SQLExample",
    # Query planning
    "QueryPlanner",
    # SQL generation
    "MockSQLGenerator",
    "LLMSQLGenerator",
    "create_sql_generator",
    # SQL parsing
    "SQLParser",
    "ParsedSQL",
    # Policy validation
    "SQLPolicyValidator",
    "PolicyContext",
    "check_sql_security_bypass_attempts",
    # Semantic validation
    "SemanticValidator",
    "MetricFormulaCheck",
    # Join validation
    "JoinValidator",
    "JoinValidationError",
    # Cost guard
    "CostGuard",
    "CostEstimate",
    "CostThreshold",
    # SQL execution
    "DuckDBExecutor",
    "PostgreSQLExecutor",
    "ExecutionConfig",
    "create_executor",
    # Result validation
    "ResultValidator",
    "ColumnValidation",
    "ResultValidationConfig",
    # SQL repair
    "SQLRepair",
    "RepairConfig",
    "RepairContext",
    "RepairStrategy",
    "RepairClassification",
    "create_repair",
    # Service
    "NL2SQLService",
    "NL2SQLConfig",
    "create_nl2sql_service",
]
