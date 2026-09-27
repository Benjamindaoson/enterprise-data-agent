"""Single governed NL2SQL orchestration path.

This module keeps deterministic and LLM generation as lanes inside one pipeline;
schema retrieval, semantic linking, policy validation, execution and result
validation are shared.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from eiw.nl2sql.contracts import (
    ExecutionStatus,
    GeneratedSQL,
    LogicalQueryPlan,
    NL2SQLRequest,
    NL2SQLResult,
    QueryLane,
    SchemaContext,
    SQLValidationErrorCategory,
    SQLValidationResult,
)
from eiw.nl2sql.cost_guard import CostGuard, CostThreshold
from eiw.nl2sql.example_retriever import ExampleRetriever
from eiw.nl2sql.executor import ExecutorProvider, create_executor
from eiw.nl2sql.generator import create_sql_generator
from eiw.nl2sql.join_validator import JoinValidator
from eiw.nl2sql.parser import ParsedSQL, SQLParser
from eiw.nl2sql.planner import QueryPlanner
from eiw.nl2sql.policy import PolicyContext, SQLPolicyValidator
from eiw.nl2sql.repair import RepairConfig, RepairContext, SQLRepair
from eiw.nl2sql.result_validator import ResultValidationConfig, ResultValidator
from eiw.nl2sql.schema_linker import SchemaLinker
from eiw.nl2sql.schema_retriever import SchemaRetriever
from eiw.nl2sql.semantic_validator import SemanticValidator
from eiw.observability.logging import get_structured_logger
from eiw.observability.otel import get_tracer, trace_span
from eiw.semantic.v2 import SemanticPackageV2

logger = get_structured_logger(__name__, "nl2sql_service")


@dataclass
class NL2SQLConfig:
    """Configuration for the unified NL2SQL service."""

    default_lane: QueryLane = QueryLane.DETERMINISTIC
    executor_type: str = "duckdb"
    executor_config: dict[str, Any] | None = None

    sql_generator_provider: str = "mock"
    llm_api_key: str | None = None
    llm_model: str = "claude-sonnet-4-20250514"

    max_rows: int = 10000
    max_complexity: int = 10
    allowed_tables: list[str] | None = None
    denied_tables: list[str] | None = None

    cost_threshold: CostThreshold | None = None
    enable_cost_guard: bool = True

    enable_repair: bool = True
    max_repair_attempts: int = 3

    allow_empty_results: bool = False
    enable_tracing: bool = True


class NL2SQLService:
    """One runtime path for retrieval, planning, validation and execution."""

    def __init__(
        self,
        config: NL2SQLConfig | None = None,
        semantic_packages: dict[str, SemanticPackageV2] | None = None,
    ) -> None:
        self._config = config or NL2SQLConfig()
        self._semantic_packages = semantic_packages or {}
        self._tracer = get_tracer()
        self._init_components()

        logger.info(
            "NL2SQL service initialized",
            extra={
                "default_lane": self._config.default_lane.value,
                "executor_type": self._config.executor_type,
                "domains": list(self._semantic_packages),
            },
        )

    def _init_components(self) -> None:
        self._schema_retriever = SchemaRetriever(self._semantic_packages)
        self._schema_linker = SchemaLinker(self._semantic_packages)
        self._example_retriever = ExampleRetriever()
        self._query_planner = QueryPlanner(self._semantic_packages)
        self._sql_generator = create_sql_generator(
            provider=self._config.sql_generator_provider,
            api_key=self._config.llm_api_key,
            model=self._config.llm_model,
        )
        self._sql_parser = SQLParser()
        self._policy_validator = SQLPolicyValidator()
        self._semantic_validator = SemanticValidator(self._semantic_packages)

        executor_config = self._config.executor_config or {}
        self._executor: ExecutorProvider = create_executor(
            self._config.executor_type,
            **executor_config,
        )
        self._cost_guard = CostGuard(
            executor=self._executor,
            thresholds=self._config.cost_threshold or CostThreshold(),
        )
        self._result_validator = ResultValidator(
            ResultValidationConfig(allow_empty=self._config.allow_empty_results)
        )
        self._sql_repair = SQLRepair(
            config=RepairConfig(
                max_repair_attempts=self._config.max_repair_attempts,
            )
        )

    def execute(self, request: NL2SQLRequest) -> NL2SQLResult:
        """Execute the configured lane through the shared governed pipeline."""

        lane = self._config.default_lane
        start_time = datetime.now()

        with trace_span(
            "nl2sql.execute",
            {
                "question": request.question[:100],
                "lane": lane.value,
                "domain": request.domain,
            },
        ):
            if request.domain not in self._semantic_packages:
                return self._error_result(
                    request=request,
                    lane=lane,
                    start_time=start_time,
                    details=f"No semantic package registered for domain: {request.domain}",
                    errors=[SQLValidationErrorCategory.SEMANTIC_MISMATCH],
                )

            try:
                return self._execute_lane(request, lane, start_time)
            except Exception as exc:
                logger.exception("NL2SQL pipeline failed")
                return self._error_result(
                    request=request,
                    lane=lane,
                    start_time=start_time,
                    details=f"Pipeline error: {type(exc).__name__}: {exc}",
                    errors=[SQLValidationErrorCategory.EXECUTION_ERROR],
                )

    def _execute_lane(
        self,
        request: NL2SQLRequest,
        lane: QueryLane,
        start_time: datetime,
    ) -> NL2SQLResult:
        schema, metrics, dimensions = self._resolve_schema(request)

        plan = self._query_planner.plan(
            question=request.question,
            domain=request.domain,
            schema=schema,
            resolved_metrics=metrics,
            resolved_dimensions=dimensions,
            time_range_start=request.time_range_start,
            time_range_end=request.time_range_end,
        )
        examples = self._approved_examples(
            request.domain,
            metrics,
            list(schema.tables),
        )

        generated = self._sql_generator.generate(
            question=request.question,
            schema_context=schema,
            logical_plan=plan,
            examples=examples,
            policy_constraints={
                "allowed_tables": self._effective_allowed_tables(schema),
                "denied_tables": self._config.denied_tables,
                "max_rows": min(request.max_rows, self._config.max_rows),
            },
        )

        repair_attempts = []
        max_attempts = (
            self._config.max_repair_attempts if self._config.enable_repair else 0
        )

        for attempt_index in range(max_attempts + 1):
            parsed = self._sql_parser.parse(generated.sql)
            if parsed is None:
                validation = SQLValidationResult(
                    is_valid=False,
                    status=ExecutionStatus.REJECTED,
                    errors=[SQLValidationErrorCategory.SYNTAX_ERROR],
                    details="SQL parsing failed",
                )
            else:
                validation = self._validate_sql(
                    request=request,
                    lane=lane,
                    schema=schema,
                    plan=plan,
                    generated=generated,
                    parsed=parsed,
                    metrics=metrics,
                    dimensions=dimensions,
                )

            if not validation.is_valid:
                if self._is_non_repairable(validation.errors):
                    return self._result(
                        request=request,
                        lane=lane,
                        plan=plan,
                        generated=generated,
                        validation=validation,
                        repair_attempts=repair_attempts,
                        start_time=start_time,
                    )

                repair = None
                if attempt_index < max_attempts:
                    repair = self._sql_repair.repair(
                        sql=generated.sql,
                        errors=validation.errors,
                        context=RepairContext(
                            original_sql=generated.sql,
                            error_category=validation.errors[0],
                            error_message=validation.details,
                            domain=request.domain,
                            metrics=metrics,
                            dimensions=dimensions,
                            policy_context=self._create_policy_context(request, schema),
                        ),
                    )
                if repair is None:
                    return self._result(
                        request=request,
                        lane=lane,
                        plan=plan,
                        generated=generated,
                        validation=validation,
                        repair_attempts=repair_attempts,
                        start_time=start_time,
                    )

                repair_attempts.append(repair)
                generated = self._with_repaired_sql(generated, repair.repaired_sql)
                continue

            execution = self._executor.execute(generated.sql)
            if execution.success:
                result_validation = self._result_validator.validate(
                    result=execution,
                    time_grain=plan.grain,
                )
                final_status = (
                    ExecutionStatus.VALID
                    if result_validation.status == ExecutionStatus.VALID
                    else ExecutionStatus.REJECTED
                )
                return NL2SQLResult(
                    request=request,
                    query_lane=lane,
                    logical_plan=plan,
                    generated_sql=generated,
                    validation=validation,
                    execution=execution,
                    result_validation=result_validation,
                    repair_attempts=repair_attempts,
                    final_sql=generated.sql,
                    final_status=final_status,
                    pipeline_duration_ms=self._elapsed_ms(start_time),
                )

            execution_error = (
                execution.error_category or SQLValidationErrorCategory.EXECUTION_ERROR
            )
            if self._config.enable_repair and attempt_index < max_attempts:
                repair = self._sql_repair.repair(
                    sql=generated.sql,
                    errors=[execution_error],
                    execution_result=execution,
                    context=RepairContext(
                        original_sql=generated.sql,
                        error_category=execution_error,
                        error_message=execution.error or "",
                        domain=request.domain,
                        metrics=metrics,
                        dimensions=dimensions,
                    ),
                )
                if repair is not None:
                    repair_attempts.append(repair)
                    generated = self._with_repaired_sql(
                        generated,
                        repair.repaired_sql,
                    )
                    continue

            final_status = (
                ExecutionStatus.TIMEOUT_ERROR
                if execution_error == SQLValidationErrorCategory.TIMEOUT
                else ExecutionStatus.EXECUTION_ERROR
            )
            return NL2SQLResult(
                request=request,
                query_lane=lane,
                logical_plan=plan,
                generated_sql=generated,
                validation=validation,
                execution=execution,
                repair_attempts=repair_attempts,
                final_sql=generated.sql,
                final_status=final_status,
                pipeline_duration_ms=self._elapsed_ms(start_time),
            )

        return self._error_result(
            request=request,
            lane=lane,
            start_time=start_time,
            details="Bounded repair attempts exhausted",
            errors=[SQLValidationErrorCategory.EXECUTION_ERROR],
            plan=plan,
            generated=generated,
            repair_attempts=repair_attempts,
        )

    def _resolve_schema(
        self,
        request: NL2SQLRequest,
    ) -> tuple[SchemaContext, list[str], list[str]]:
        initial_schema = self._schema_retriever.retrieve(
            domain=request.domain,
            metrics=request.resolved_metrics,
            dimensions=request.resolved_dimensions,
            user_roles=request.user_roles,
            business_context=request.business_context,
            question=request.question,
        )

        candidate_metrics = list(
            initial_schema.retrieval_trace.get(
                "selected_metrics",
                request.resolved_metrics,
            )
        )
        candidate_dimensions = list(
            initial_schema.retrieval_trace.get(
                "selected_dimensions",
                request.resolved_dimensions,
            )
        )

        linked = self._schema_linker.link(
            question=request.question,
            domain=request.domain,
            resolved_metrics=candidate_metrics,
            resolved_dimensions=candidate_dimensions,
        )
        metrics = list(dict.fromkeys(linked.resolved_metrics))
        dimensions = list(dict.fromkeys(linked.resolved_dimensions))

        # Rebuild once from the resolved semantic IDs so the schema context is
        # authoritative even when retrieval supplied the initial candidates.
        schema = self._schema_retriever.retrieve(
            domain=request.domain,
            metrics=metrics,
            dimensions=dimensions,
            user_roles=request.user_roles,
            business_context=request.business_context,
            question=request.question,
        )
        schema.retrieval_trace["linked_tables"] = linked.linked_tables
        schema.retrieval_trace["linked_columns"] = linked.linked_columns
        schema.retrieval_trace["ambiguities"] = linked.ambiguities
        return schema, metrics, dimensions

    def _validate_sql(
        self,
        *,
        request: NL2SQLRequest,
        lane: QueryLane,
        schema: SchemaContext,
        plan: LogicalQueryPlan,
        generated: GeneratedSQL,
        parsed: ParsedSQL,
        metrics: list[str],
        dimensions: list[str],
    ) -> SQLValidationResult:
        if parsed.statement_count != 1:
            return SQLValidationResult(
                is_valid=False,
                status=ExecutionStatus.REJECTED,
                errors=[SQLValidationErrorCategory.SECURITY_POLICY],
                details="Only one SQL statement is allowed",
            )

        policy = self._policy_validator.validate(
            sql=generated.sql,
            parsed_sql=parsed,
            schema=schema,
            policy_context=self._create_policy_context(request, schema),
        )
        if not policy.is_valid:
            return policy

        warnings = list(policy.warnings)
        policy_checks = dict(policy.policy_checks)

        if lane == QueryLane.GOVERNED_NL2SQL:
            semantic = self._semantic_validator.validate(
                sql=generated.sql,
                domain=request.domain,
                metrics=metrics,
                dimensions=dimensions,
                grain=plan.grain,
                time_range_start=request.time_range_start,
                time_range_end=request.time_range_end,
            )
            warnings.extend(semantic.warnings)
            if not semantic.is_valid:
                return semantic

            join_result = JoinValidator(schema).validate_joins(parsed)
            warnings.extend(join_result.warnings)
            if not join_result.is_valid:
                return join_result

            if self._config.enable_cost_guard:
                cost = self._cost_guard.validate(
                    generated.sql,
                    dialect=self._config.executor_type,
                )
                warnings.extend(cost.warnings)
                if not cost.is_valid:
                    return cost

        return SQLValidationResult(
            is_valid=True,
            status=ExecutionStatus.VALID,
            warnings=warnings,
            details="Governed validation passed",
            policy_checks=policy_checks,
        )

    def _create_policy_context(
        self,
        request: NL2SQLRequest,
        schema: SchemaContext,
    ) -> PolicyContext:
        return PolicyContext(
            user_roles=request.user_roles or ["viewer"],
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            allowed_tables=self._effective_allowed_tables(schema),
            denied_tables=self._config.denied_tables,
            max_rows=min(request.max_rows, self._config.max_rows),
            max_complexity=min(
                request.max_complexity,
                self._config.max_complexity,
            ),
        )

    def _effective_allowed_tables(self, schema: SchemaContext) -> list[str]:
        schema_tables = set(schema.tables)
        if self._config.allowed_tables is None:
            return sorted(schema_tables)
        return sorted(schema_tables & set(self._config.allowed_tables))

    def _approved_examples(
        self,
        domain: str,
        metrics: list[str],
        tables: list[str],
    ) -> list[GeneratedSQL]:
        retrieved = self._example_retriever.retrieve(
            domain=domain,
            related_metrics=metrics,
            related_tables=tables,
            max_examples=3,
        )
        return [
            GeneratedSQL(
                sql=example.sql,
                tables_used=example.related_tables,
                metrics_calculated=example.related_metrics,
                confidence=1.0,
                explanation=example.description,
                provider="approved_example",
                prompt_version=example.version,
                sql_hash=hashlib.sha256(example.sql.encode()).hexdigest()[:16],
            )
            for example in retrieved.examples
        ]

    @staticmethod
    def _is_non_repairable(
        errors: list[SQLValidationErrorCategory],
    ) -> bool:
        return any(
            error
            in {
                SQLValidationErrorCategory.PERMISSION_DENIED,
                SQLValidationErrorCategory.SECURITY_POLICY,
            }
            for error in errors
        )

    @staticmethod
    def _with_repaired_sql(
        generated: GeneratedSQL,
        sql: str,
    ) -> GeneratedSQL:
        return GeneratedSQL(
            sql=sql,
            tables_used=generated.tables_used,
            columns_used=generated.columns_used,
            metrics_calculated=generated.metrics_calculated,
            joins_used=generated.joins_used,
            where_clauses=generated.where_clauses,
            confidence=max(0.0, generated.confidence * 0.9),
            explanation=f"Repaired from prior candidate: {generated.explanation}",
            provider=generated.provider,
            model=generated.model,
            prompt_version=generated.prompt_version,
            sql_hash=hashlib.sha256(sql.encode()).hexdigest()[:16],
        )

    def _result(
        self,
        *,
        request: NL2SQLRequest,
        lane: QueryLane,
        plan: LogicalQueryPlan,
        generated: GeneratedSQL,
        validation: SQLValidationResult,
        repair_attempts: list[Any],
        start_time: datetime,
    ) -> NL2SQLResult:
        return NL2SQLResult(
            request=request,
            query_lane=lane,
            logical_plan=plan,
            generated_sql=generated,
            validation=validation,
            repair_attempts=repair_attempts,
            final_sql=generated.sql,
            final_status=ExecutionStatus.REJECTED,
            pipeline_duration_ms=self._elapsed_ms(start_time),
        )

    def _error_result(
        self,
        *,
        request: NL2SQLRequest,
        lane: QueryLane,
        start_time: datetime,
        details: str,
        errors: list[SQLValidationErrorCategory],
        plan: LogicalQueryPlan | None = None,
        generated: GeneratedSQL | None = None,
        repair_attempts: list[Any] | None = None,
    ) -> NL2SQLResult:
        return NL2SQLResult(
            request=request,
            query_lane=lane,
            logical_plan=plan,
            generated_sql=generated,
            validation=SQLValidationResult(
                is_valid=False,
                status=ExecutionStatus.REJECTED,
                errors=errors,
                details=details,
            ),
            repair_attempts=repair_attempts or [],
            final_sql=generated.sql if generated else "",
            final_status=ExecutionStatus.REJECTED,
            pipeline_duration_ms=self._elapsed_ms(start_time),
        )

    @staticmethod
    def _elapsed_ms(start_time: datetime) -> float:
        return (datetime.now() - start_time).total_seconds() * 1000

    def health_check(self) -> dict[str, Any]:
        components = {
            "executor": self._executor.health_check(),
            "semantic_packages": bool(self._semantic_packages),
            "sql_generator": self._sql_generator is not None,
            "hybrid_retrieval": self._schema_retriever is not None,
        }
        return {
            "service": "nl2sql",
            "status": "healthy" if all(components.values()) else "degraded",
            "components": components,
        }


def create_nl2sql_service(
    config: NL2SQLConfig | None = None,
    semantic_packages: dict[str, SemanticPackageV2] | None = None,
) -> NL2SQLService:
    return NL2SQLService(
        config=config,
        semantic_packages=semantic_packages,
    )
