"""NL2SQL Service - Orchestrates the full NL2SQL pipeline.

This module provides:
- Full pipeline orchestration
- Query lane selection (deterministic vs governed)
- Error handling and recovery
- OpenTelemetry tracing
- Comprehensive logging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

from eiw.nl2sql.contracts import (
    NL2SQLRequest,
    NL2SQLResult,
    QueryLane,
    ExecutionStatus,
    SQLValidationErrorCategory,
    GeneratedSQL,
    ExecutionResult,
    SchemaContext,
)
from eiw.semantic.v2 import SemanticPackageV2
from eiw.observability.otel import trace_span, get_tracer
from eiw.observability.logging import get_structured_logger

# Import NL2SQL components
from eiw.nl2sql.schema_retriever import SchemaRetriever
from eiw.nl2sql.schema_linker import SchemaLinker
from eiw.nl2sql.example_retriever import ExampleRetriever
from eiw.nl2sql.planner import QueryPlanner
from eiw.nl2sql.generator import create_sql_generator
from eiw.nl2sql.parser import SQLParser
from eiw.nl2sql.policy import SQLPolicyValidator, PolicyContext
from eiw.nl2sql.semantic_validator import SemanticValidator
from eiw.nl2sql.join_validator import JoinValidator
from eiw.nl2sql.cost_guard import CostGuard, CostThreshold
from eiw.nl2sql.executor import create_executor, ExecutorProvider
from eiw.nl2sql.result_validator import ResultValidator, ResultValidationConfig
from eiw.nl2sql.repair import SQLRepair, RepairConfig, RepairContext


logger = get_structured_logger(__name__, "nl2sql_service")


@dataclass
class NL2SQLConfig:
    """Configuration for NL2SQL service."""

    # Lane configuration
    default_lane: QueryLane = QueryLane.DETERMINISTIC

    # Executor configuration
    executor_type: str = "duckdb"
    executor_config: dict[str, Any] | None = None

    # SQL generation
    sql_generator_provider: str = "mock"  # "mock" or "llm"
    llm_api_key: str | None = None
    llm_model: str = "claude-sonnet-4-20250514"

    # Policy configuration
    max_rows: int = 10000
    max_complexity: int = 10
    allowed_tables: list[str] | None = None
    denied_tables: list[str] | None = None

    # Cost guard configuration
    cost_threshold: CostThreshold | None = None
    enable_cost_guard: bool = True

    # Repair configuration
    enable_repair: bool = True
    max_repair_attempts: int = 3

    # Result validation
    allow_empty_results: bool = False

    # Tracing
    enable_tracing: bool = True


class NL2SQLService:
    """Orchestrates the NL2SQL pipeline.

    This service coordinates:
    1. Schema retrieval
    2. Schema linking
    3. Example retrieval
    4. Query planning
    5. SQL generation
    6. SQL parsing and validation
    7. Policy validation
    8. Semantic validation
    9. Join validation
    10. Cost analysis
    11. SQL execution
    12. Result validation
    13. SQL repair (on failure)
    """

    def __init__(
        self,
        config: NL2SQLConfig | None = None,
        semantic_packages: dict[str, SemanticPackageV2] | None = None,
    ) -> None:
        """Initialize NL2SQL service.

        Args:
            config: Service configuration
            semantic_packages: Semantic packages by domain
        """
        self._config = config or NL2SQLConfig()
        self._semantic_packages = semantic_packages or {}
        self._tracer = get_tracer()

        # Initialize components
        self._init_components()

        logger.info(
            "NL2SQL service initialized",
            extra={
                "config": {
                    "default_lane": self._config.default_lane.value,
                    "executor_type": self._config.executor_type,
                    "enable_repair": self._config.enable_repair,
                },
                "domains": list(self._semantic_packages.keys()),
            }
        )

    def _init_components(self) -> None:
        """Initialize all pipeline components."""
        # Schema retriever
        self._schema_retriever = SchemaRetriever(self._semantic_packages)

        # Schema linker
        self._schema_linker = SchemaLinker(self._semantic_packages)

        # Example retriever
        self._example_retriever = ExampleRetriever()

        # Query planner
        self._query_planner = QueryPlanner(self._semantic_packages)

        # SQL generator
        self._sql_generator = create_sql_generator(
            provider=self._config.sql_generator_provider,
            api_key=self._config.llm_api_key,
            model=self._config.llm_model,
        )

        # SQL parser
        self._sql_parser = SQLParser()

        # Policy validator
        self._policy_validator = SQLPolicyValidator()

        # Semantic validator
        self._semantic_validator = SemanticValidator(self._semantic_packages)

        # Executor
        executor_config = self._config.executor_config or {}
        self._executor: ExecutorProvider = create_executor(
            self._config.executor_type,
            **executor_config,
        )

        # Cost guard
        self._cost_guard = CostGuard(
            executor=self._executor,
            thresholds=self._config.cost_threshold or CostThreshold(),
        )

        # Result validator
        result_config = ResultValidationConfig(
            allow_empty=self._config.allow_empty_results,
        )
        self._result_validator = ResultValidator(result_config)

        # SQL repair
        repair_config = RepairConfig(
            max_repair_attempts=self._config.max_repair_attempts,
        )
        self._sql_repair = SQLRepair(config=repair_config)

    def execute(
        self,
        request: NL2SQLRequest,
    ) -> NL2SQLResult:
        """Execute NL2SQL pipeline.

        Args:
            request: NL2SQL request

        Returns:
            NL2SQL result
        """
        lane = self._config.default_lane

        with trace_span("nl2sql.execute", {
            "question": request.question[:100],
            "lane": lane.value,
            "domain": request.domain,
        }):
            start_time = datetime.now()

            logger.info(
                f"Starting NL2SQL execution",
                extra={
                    "question": request.question,
                    "lane": lane.value,
                    "domain": request.domain,
                }
            )

            try:
                if lane == QueryLane.DETERMINISTIC:
                    return self._execute_deterministic(request, start_time)
                else:
                    return self._execute_governed(request, start_time)

            except Exception as e:
                logger.error(f"NL2SQL execution failed: {e}")
                return NL2SQLResult(
                    request=request,
                    final_status=ExecutionStatus.REJECTED,
                    pipeline_duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

    def _execute_deterministic(
        self,
        request: NL2SQLRequest,
        start_time: datetime,
    ) -> NL2SQLResult:
        """Execute deterministic query lane.

        Args:
            request: NL2SQL request
            start_time: Start time

        Returns:
            NL2SQL result
        """
        with trace_span("nl2sql.deterministic_lane"):
            # Step 1: Schema retrieval
            schema = self._schema_retriever.retrieve(
                domain=request.domain,
                user_context=request.user_context,
                requested_tables=request.requested_tables,
            )

            # Step 2: Schema linking
            link_result = self._schema_linker.link(
                question=request.question,
                domain=request.domain,
                schema=schema,
            )

            # Step 3: Query planning
            plan = self._query_planner.plan(
                question=request.question,
                domain=request.domain,
                schema=schema,
                resolved_metrics=link_result.resolved_metrics,
                resolved_dimensions=link_result.resolved_dimensions,
                time_range_start=request.time_range_start,
                time_range_end=request.time_range_end,
            )

            # Step 4: SQL generation
            examples = self._example_retriever.retrieve(
                domain=request.domain,
                metrics=link_result.resolved_metrics,
                dimensions=link_result.resolved_dimensions,
                limit=3,
            )

            generated_sql = self._sql_generator.generate(
                question=request.question,
                schema_context=schema,
                logical_plan=plan,
                examples=examples,
                policy_constraints={},
            )

            # Step 5: SQL parsing and validation
            parsed_sql = self._sql_parser.parse(generated_sql.sql)
            if not parsed_sql:
                return self._create_error_result(
                    request, start_time,
                    "SQL parsing failed",
                    ExecutionStatus.REJECTED,
                    [SQLValidationErrorCategory.SYNTAX_ERROR],
                )

            # Step 6: Execute and return
            return self._execute_and_validate(
                request, schema, generated_sql, parsed_sql, start_time
            )

    def _execute_governed(
        self,
        request: NL2SQLRequest,
        start_time: datetime,
    ) -> NL2SQLResult:
        """Execute governed query lane with full validation.

        Args:
            request: NL2SQL request
            start_time: Start time

        Returns:
            NL2SQL result
        """
        with trace_span("nl2sql.governed_lane"):
            repair_attempt = None
            current_attempt = 0
            max_attempts = self._config.max_repair_attempts + 1

            while current_attempt < max_attempts:
                current_attempt += 1

                logger.info(f"Governed lane attempt {current_attempt}/{max_attempts}")

                # Step 1: Schema retrieval
                schema = self._schema_retriever.retrieve(
                    domain=request.domain,
                    user_context=request.user_context,
                    requested_tables=request.requested_tables,
                )

                # Step 2: Schema linking
                link_result = self._schema_linker.link(
                    question=request.question,
                    domain=request.domain,
                    schema=schema,
                )

                # Step 3: Query planning
                plan = self._query_planner.plan(
                    question=request.question,
                    domain=request.domain,
                    schema=schema,
                    resolved_metrics=link_result.resolved_metrics,
                    resolved_dimensions=link_result.resolved_dimensions,
                    time_range_start=request.time_range_start,
                    time_range_end=request.time_range_end,
                )

                # Step 4: SQL generation
                examples = self._example_retriever.retrieve(
                    domain=request.domain,
                    metrics=link_result.resolved_metrics,
                    dimensions=link_result.resolved_dimensions,
                    limit=3,
                )

                policy_constraints = {
                    "allowed_tables": self._config.allowed_tables,
                    "denied_tables": self._config.denied_tables,
                    "max_rows": self._config.max_rows,
                }

                generated_sql = self._sql_generator.generate(
                    question=request.question,
                    schema_context=schema,
                    logical_plan=plan,
                    examples=examples,
                    policy_constraints=policy_constraints,
                )

                # Step 5: SQL parsing
                parsed_sql = self._sql_parser.parse(generated_sql.sql)
                if not parsed_sql:
                    return self._create_error_result(
                        request, start_time,
                        "SQL parsing failed",
                        ExecutionStatus.REJECTED,
                        [SQLValidationErrorCategory.SYNTAX_ERROR],
                    )

                # Step 6: Policy validation
                policy_ctx = self._create_policy_context(request)
                policy_result = self._policy_validator.validate(
                    sql=generated_sql.sql,
                    parsed_sql=parsed_sql,
                    schema=schema,
                    policy_context=policy_ctx,
                )

                if not policy_result.is_valid:
                    logger.warning(f"Policy validation failed: {policy_result.errors}")

                    if self._config.enable_repair and current_attempt < max_attempts:
                        repair = self._sql_repair.repair(
                            sql=generated_sql.sql,
                            errors=policy_result.errors,
                            context=RepairContext(
                                original_sql=generated_sql.sql,
                                error_category=policy_result.errors[0],
                                error_message=policy_result.details or "",
                                domain=request.domain,
                                metrics=link_result.resolved_metrics,
                                dimensions=link_result.resolved_dimensions,
                            ),
                        )
                        if repair:
                            generated_sql = GeneratedSQL(
                                sql=repair.repaired_sql,
                                tables_used=generated_sql.tables_used,
                                columns_used=generated_sql.columns_used,
                                metrics_calculated=generated_sql.metrics_calculated,
                                confidence=generated_sql.confidence * 0.9,
                                explanation=f"Repaired: {repair.details}",
                                provider=generated_sql.provider,
                                model=generated_sql.model,
                                prompt_version=generated_sql.prompt_version,
                                sql_hash=generated_sql.sql_hash,
                            )
                            repair_attempt = repair
                            continue

                    return self._create_error_result(
                        request, start_time,
                        f"Policy validation failed: {policy_result.details}",
                        ExecutionStatus.REJECTED,
                        policy_result.errors,
                        generated_sql=generated_sql,
                    )

                # Step 7: Semantic validation
                semantic_result = self._semantic_validator.validate(
                    sql=generated_sql.sql,
                    domain=request.domain,
                    metrics=link_result.resolved_metrics,
                    dimensions=link_result.resolved_dimensions,
                    grain=plan.grain,
                    time_range_start=request.time_range_start,
                    time_range_end=request.time_range_end,
                )

                if not semantic_result.is_valid:
                    logger.warning(f"Semantic validation failed: {semantic_result.errors}")

                    if self._config.enable_repair and current_attempt < max_attempts:
                        repair = self._sql_repair.repair(
                            sql=generated_sql.sql,
                            errors=semantic_result.errors,
                            context=RepairContext(
                                original_sql=generated_sql.sql,
                                error_category=semantic_result.errors[0],
                                error_message=semantic_result.details or "",
                                domain=request.domain,
                                metrics=link_result.resolved_metrics,
                                dimensions=link_result.resolved_dimensions,
                            ),
                        )
                        if repair:
                            generated_sql = GeneratedSQL(
                                sql=repair.repaired_sql,
                                tables_used=generated_sql.tables_used,
                                columns_used=generated_sql.columns_used,
                                metrics_calculated=generated_sql.metrics_calculated,
                                confidence=generated_sql.confidence * 0.9,
                                explanation=f"Repaired: {repair.details}",
                                provider=generated_sql.provider,
                                model=generated_sql.model,
                                prompt_version=generated_sql.prompt_version,
                                sql_hash=generated_sql.sql_hash,
                            )
                            repair_attempt = repair
                            continue

                    return self._create_error_result(
                        request, start_time,
                        f"Semantic validation failed: {semantic_result.details}",
                        ExecutionStatus.REJECTED,
                        semantic_result.errors,
                        generated_sql=generated_sql,
                    )

                # Step 8: Join validation
                join_validator = JoinValidator(schema)
                join_result = join_validator.validate_joins(parsed_sql)

                if not join_result.is_valid:
                    logger.warning(f"Join validation failed: {join_result.errors}")

                # Step 9: Cost guard (if enabled)
                if self._config.enable_cost_guard:
                    cost_result = self._cost_guard.validate(generated_sql.sql)
                    if not cost_result.is_valid:
                        logger.warning(f"Cost guard validation failed: {cost_result.warnings}")

                # Step 10: Execute and validate
                result = self._execute_and_validate(
                    request, schema, generated_sql, parsed_sql, start_time
                )

                # Check if execution succeeded
                if result.status == ExecutionStatus.SUCCESS:
                    result.repair_attempt = repair_attempt
                    return result

                # If execution failed, try repair
                if self._config.enable_repair and current_attempt < max_attempts:
                    execution_errors = []
                    if result.execution_result:
                        if result.execution_result.error_category:
                            execution_errors = [result.execution_result.error_category]
                        elif result.status == ExecutionStatus.TIMEOUT:
                            execution_errors = [SQLValidationErrorCategory.COMPLEXITY_EXCEEDED]

                    if execution_errors:
                        repair = self._sql_repair.repair(
                            sql=generated_sql.sql,
                            errors=execution_errors,
                            execution_result=result.execution_result,
                            context=RepairContext(
                                original_sql=generated_sql.sql,
                                error_category=execution_errors[0],
                                error_message=result.error_message or "",
                                domain=request.domain,
                                metrics=link_result.resolved_metrics,
                                dimensions=link_result.resolved_dimensions,
                            ),
                        )
                        if repair:
                            generated_sql = GeneratedSQL(
                                sql=repair.repaired_sql,
                                tables_used=generated_sql.tables_used,
                                columns_used=generated_sql.columns_used,
                                metrics_calculated=generated_sql.metrics_calculated,
                                confidence=generated_sql.confidence * 0.9,
                                explanation=f"Repaired: {repair.details}",
                                provider=generated_sql.provider,
                                model=generated_sql.model,
                                prompt_version=generated_sql.prompt_version,
                                sql_hash=generated_sql.sql_hash,
                            )
                            repair_attempt = repair
                            continue

                # No more attempts or repair not possible
                return result

            # Max attempts exceeded
            return self._create_error_result(
                request, start_time,
                f"Max repair attempts ({self._config.max_repair_attempts}) exceeded",
                ExecutionStatus.REJECTED,
                [SQLValidationErrorCategory.COMPLEXITY_EXCEEDED],
                generated_sql=generated_sql,
                repair_attempt=repair_attempt,
            )

    def _execute_and_validate(
        self,
        request: NL2SQLRequest,
        schema: SchemaContext,
        generated_sql: GeneratedSQL,
        parsed_sql: Any,
        start_time: datetime,
    ) -> NL2SQLResult:
        """Execute SQL and validate results.

        Args:
            request: NL2SQL request
            schema: Schema context
            generated_sql: Generated SQL
            parsed_sql: Parsed SQL
            start_time: Start time

        Returns:
            NL2SQL result
        """
        with trace_span("nl2sql.execute_and_validate"):
            # Execute SQL
            execution_result = self._executor.execute(generated_sql.sql)

            if execution_result.status != ExecutionStatus.SUCCESS:
                return NL2SQLResult(
                    question=request.question,
                    generated_sql=generated_sql,
                    execution_result=execution_result,
                    status=execution_result.status,
                    error_message=execution_result.error_message,
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

            # Validate result
            result_validation = self._result_validator.validate(
                result=execution_result,
                expected_columns=None,  # Would come from semantic layer
            )

            if not result_validation.is_valid:
                return NL2SQLResult(
                    question=request.question,
                    generated_sql=generated_sql,
                    execution_result=execution_result,
                    status=ExecutionStatus.WARNING,
                    error_message=result_validation.error_message,
                    warnings=result_validation.warnings,
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

            return NL2SQLResult(
                question=request.question,
                generated_sql=generated_sql,
                execution_result=execution_result,
                status=ExecutionStatus.SUCCESS,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

    def _create_policy_context(self, request: NL2SQLRequest) -> PolicyCtx:
        """Create policy context from request.

        Args:
            request: NL2SQL request

        Returns:
            Policy context
        """
        return PolicyCtx(
            user_roles=request.user_context.get("roles", ["viewer"]) if request.user_context else ["viewer"],
            user_id=request.user_context.get("user_id") if request.user_context else None,
            tenant_id=request.user_context.get("tenant_id") if request.user_context else None,
            allowed_tables=self._config.allowed_tables,
            denied_tables=self._config.denied_tables,
            max_rows=self._config.max_rows,
            max_complexity=self._config.max_complexity,
        )

    def _create_error_result(
        self,
        request: NL2SQLRequest,
        start_time: datetime,
        error_message: str,
        status: ExecutionStatus,
        errors: list[SQLValidationErrorCategory],
        generated_sql: GeneratedSQL | None = None,
        repair_attempt: Any = None,
    ) -> NL2SQLResult:
        """Create error result.

        Args:
            request: NL2SQL request
            start_time: Start time
            error_message: Error message
            status: Execution status
            errors: Error categories
            generated_sql: Generated SQL if available
            repair_attempt: Repair attempt if available

        Returns:
            NL2SQL result
        """
        return NL2SQLResult(
            question=request.question,
            generated_sql=generated_sql,
            status=status,
            error_message=error_message,
            errors=errors,
            repair_attempt=repair_attempt,
            execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
        )

    def health_check(self) -> dict[str, Any]:
        """Check service health.

        Returns:
            Health status
        """
        health = {
            "service": "nl2sql",
            "status": "healthy",
            "components": {},
        }

        # Check executor
        health["components"]["executor"] = self._executor.health_check()

        # Check semantic packages
        health["components"]["semantic_packages"] = len(self._semantic_packages) > 0

        # Check SQL generator
        health["components"]["sql_generator"] = self._sql_generator is not None

        # Overall status
        if not all(health["components"].values()):
            health["status"] = "degraded"

        return health


def create_nl2sql_service(
    config: NL2SQLConfig | None = None,
    semantic_packages: dict[str, SemanticPackageV2] | None = None,
) -> NL2SQLService:
    """Create NL2SQL service instance.

    Args:
        config: Service configuration
        semantic_packages: Semantic packages by domain

    Returns:
        NL2SQL service
    """
    return NL2SQLService(config=config, semantic_packages=semantic_packages)
