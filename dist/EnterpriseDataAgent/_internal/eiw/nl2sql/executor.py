"""SQL Executor - Executes SQL against DuckDB and PostgreSQL.

This module provides:
- Read-only SQL execution
- DuckDB support
- PostgreSQL support
- Query timeout and cancellation
- Result normalization
- Error handling
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import threading
import uuid

from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    SQLValidationResult,
    ExecutionResult,
    ExecutionStatus,
    ExecutorProvider,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "sql_executor")


@dataclass
class ExecutionConfig:
    """Configuration for SQL execution."""

    timeout_ms: int = 30000  # 30 second default timeout
    max_rows: int = 10000
    fetch_size: int = 1000
    read_only: bool = True


class DuckDBExecutor(ExecutorProvider):
    """SQL executor using DuckDB.

    DuckDB is used for:
    - In-memory analytical queries
    - Fast local execution
    - Parquet/CSV file access
    """

    def __init__(
        self,
        database: str = ":memory:",
        config: ExecutionConfig | None = None,
        **kwargs,
    ) -> None:
        """Initialize DuckDB executor.

        Args:
            database: Database path or ":memory:"
            config: Execution configuration
        """
        super().__init__(
            provider_name="duckdb",
            executor_type="duckdb",
            executor_version="1.0",
            **kwargs,
        )
        self._database = database
        self._config = config or ExecutionConfig()
        self._conn: Any = None
        self._lock = threading.Lock()
        self._init_database()

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook for Pydantic model."""
        # Initialize database connection after Pydantic initialization
        pass

    def _init_database(self) -> None:
        """Initialize database connection."""
        try:
            import duckdb
            # For in-memory database, we need to allow writes
            read_only = self._config.read_only and self._database != ":memory:"
            self._conn = duckdb.connect(self._database, read_only=read_only)
            self._duckdb = duckdb
            logger.info(f"DuckDB executor initialized: {self._database}")
        except ImportError:
            logger.warning("DuckDB not installed - using mock executor")
            self._duckdb = None
            self._conn = None

    def execute(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute SQL synchronously.

        Args:
            sql: SQL to execute
            params: Query parameters

        Returns:
            Execution result
        """
        return self.execute_sync(sql, timeout_ms=self._config.timeout_ms, params=params)

    def execute_sync(
        self,
        sql: str,
        timeout_ms: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute SQL with timeout.

        Args:
            sql: SQL to execute
            timeout_ms: Timeout in milliseconds
            params: Query parameters

        Returns:
            Execution result
        """
        with trace_span("nl2sql.execute", {
            "executor": "duckdb",
            "sql_length": len(sql),
            "timeout_ms": timeout_ms or self._config.timeout_ms,
        }):
            if self._duckdb is None:
                return ExecutionResult(
                    success=False,
                    error="DuckDB not available",
                    error_category=SQLValidationErrorCategory.EXECUTION_ERROR,
                    execution_time_ms=0,
                    row_count=0,
                    rows=[],
                    columns=[],
                )

            timeout_ms = timeout_ms or self._config.timeout_ms
            result_container: dict[str, Any] = {}
            exception_holder: dict[str, Exception | None] = {"exception": None}

            def execute_query():
                try:
                    with self._lock:
                        # Set timeout
                        if hasattr(self._conn, 'statement_timeout'):
                            self._conn.execute(f"SET statement_timeout = '{timeout_ms}ms'")

                        # Execute query
                        if params:
                            cursor = self._conn.execute(sql, params)
                        else:
                            cursor = self._conn.execute(sql)

                        # Fetch results
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchmany(self._config.fetch_size)
                            row_count = len(rows)

                            # Fetch remaining if needed
                            while len(rows) < self._config.max_rows:
                                more_rows = cursor.fetchmany(self._config.fetch_size)
                                if not more_rows:
                                    break
                                rows.extend(more_rows)

                            result_container["columns"] = columns
                            result_container["rows"] = rows
                            result_container["row_count"] = len(rows)
                        else:
                            result_container["columns"] = []
                            result_container["rows"] = []
                            result_container["row_count"] = 0

                except Exception as e:
                    exception_holder["exception"] = e

            # Execute with timeout
            thread = threading.Thread(target=execute_query)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout_ms / 1000.0)

            if thread.is_alive():
                # Timeout - try to cancel
                logger.warning(f"Query timed out after {timeout_ms}ms")
                return ExecutionResult(
                    success=False,
                    error=f"Query exceeded timeout of {timeout_ms}ms",
                    error_category=SQLValidationErrorCategory.TIMEOUT,
                    execution_time_ms=timeout_ms,
                    row_count=0,
                    rows=[],
                    columns=[],
                )

            if exception_holder["exception"]:
                error = exception_holder["exception"]
                error_msg = str(error)

                # Check for specific error types
                if "permission denied" in error_msg.lower():
                    return ExecutionResult(
                        success=False,
                        error=error_msg,
                        error_category=SQLValidationErrorCategory.PERMISSION_DENIED,
                        execution_time_ms=0,
                        row_count=0,
                        rows=[],
                        columns=[],
                    )

                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    error_category=SQLValidationErrorCategory.EXECUTION_ERROR,
                    execution_time_ms=0,
                    row_count=0,
                    rows=[],
                    columns=[],
                )

            # Success
            import time
            return ExecutionResult(
                success=True,
                execution_time_ms=result_container.get("execution_time_ms", 0),
                row_count=result_container.get("row_count", 0),
                rows=result_container.get("rows", []),
                columns=result_container.get("columns", []),
            )

    def execute_async(
        self,
        sql: str,
        callback: Callable[[ExecutionResult], None],
        timeout_ms: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Execute SQL asynchronously.

        Args:
            sql: SQL to execute
            callback: Callback with result
            timeout_ms: Timeout in milliseconds
            params: Query parameters

        Returns:
            Query ID for cancellation
        """
        query_id = str(uuid.uuid4())
        timeout_ms = timeout_ms or self._config.timeout_ms

        def execute():
            result = self.execute_sync(sql, timeout_ms, params)
            callback(result)

        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()

        return query_id

    def cancel(self, query_id: str) -> bool:
        """Cancel a running query.

        Args:
            query_id: Query ID to cancel

        Returns:
            True if cancelled
        """
        # DuckDB doesn't support query cancellation directly
        # This would require connection-level cancellation
        logger.warning(f"Query cancellation requested for {query_id} - not supported in DuckDB")
        return False

    def health_check(self) -> bool:
        """Check executor health.

        Returns:
            True if healthy
        """
        try:
            if self._conn:
                with self._lock:
                    self._conn.execute("SELECT 1")
                return True
        except Exception:
            pass
        return False


class PostgreSQLExecutor(ExecutorProvider):
    """SQL executor using PostgreSQL.

    PostgreSQL is used for:
    - Production data access
    - Complex queries with CTEs
    - Larger datasets
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        user: str | None = None,
        password: str | None = None,
        config: ExecutionConfig | None = None,
    ) -> None:
        """Initialize PostgreSQL executor.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Username
            password: Password
            config: Execution configuration
        """
        super().__init__(executor_type="postgresql", executor_version="1.0")
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._config = config or ExecutionConfig()
        self._conn: Any = None
        self._psycopg2 = None
        self._init_connection()

    def _init_connection(self) -> None:
        """Initialize database connection."""
        try:
            import psycopg2
            import psycopg2.extras
            self._psycopg2 = psycopg2
            self._psycopg2_extras = psycopg2.extras

            # Build connection string
            conn_str = f"host={self._host} port={self._port} dbname={self._database}"
            if self._user:
                conn_str += f" user={self._user}"
            if self._password:
                conn_str += f" password={self._password}"
            conn_str += " sslmode=prefer"

            # Connection with read-only mode
            self._conn = psycopg2.connect(conn_str)
            self._conn.set_session(readonly=self._config.read_only, autocommit=True)

            logger.info(f"PostgreSQL executor initialized: {self._host}:{self._port}/{self._database}")
        except ImportError:
            logger.warning("psycopg2 not installed - using mock executor")
            self._psycopg2 = None
            self._conn = None

    def execute(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute SQL synchronously.

        Args:
            sql: SQL to execute
            params: Query parameters

        Returns:
            Execution result
        """
        return self.execute_sync(sql, timeout_ms=self._config.timeout_ms, params=params)

    def execute_sync(
        self,
        sql: str,
        timeout_ms: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute SQL with timeout.

        Args:
            sql: SQL to execute
            timeout_ms: Timeout in milliseconds
            params: Query parameters

        Returns:
            Execution result
        """
        with trace_span("nl2sql.execute", {
            "executor": "postgresql",
            "sql_length": len(sql),
            "timeout_ms": timeout_ms or self._config.timeout_ms,
        }):
            if self._psycopg2 is None or self._conn is None:
                return ExecutionResult(
                    success=False,
                    error="PostgreSQL not available",
                    error_category=SQLValidationErrorCategory.EXECUTION_ERROR,
                    execution_time_ms=0,
                    row_count=0,
                    rows=[],
                    columns=[],
                )

            import time
            start_time = time.time()
            timeout_ms = timeout_ms or self._config.timeout_ms

            try:
                with self._conn.cursor() as cursor:
                    # Set statement timeout
                    cursor.execute(f"SET statement_timeout = '{timeout_ms}'")

                    # Execute query
                    if params:
                        # Convert params to tuple format
                        param_tuple = tuple(params.values())
                        cursor.execute(sql, param_tuple)
                    else:
                        cursor.execute(sql)

                    # Fetch results
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchmany(self._config.fetch_size)
                        row_count = len(rows)

                        # Fetch remaining up to max_rows
                        while len(rows) < self._config.max_rows:
                            more_rows = cursor.fetchmany(self._config.fetch_size)
                            if not more_rows:
                                break
                            rows.extend(more_rows)

                        execution_time_ms = (time.time() - start_time) * 1000

                        return ExecutionResult(
                            success=True,
                            execution_time_ms=execution_time_ms,
                            row_count=len(rows),
                            rows=rows,
                            columns=columns,
                        )
                    else:
                        execution_time_ms = (time.time() - start_time) * 1000
                        return ExecutionResult(
                            success=True,
                            execution_time_ms=execution_time_ms,
                            row_count=0,
                            rows=[],
                            columns=[],
                        )

            except self._psycopg2.OperationalError as e:
                error_msg = str(e)
                if "statement timeout" in error_msg.lower():
                    return ExecutionResult(
                        success=False,
                        error=f"Query exceeded timeout of {timeout_ms}ms",
                        error_category=SQLValidationErrorCategory.TIMEOUT,
                        execution_time_ms=timeout_ms,
                        row_count=0,
                        rows=[],
                        columns=[],
                    )
                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    error_category=SQLValidationErrorCategory.EXECUTION_ERROR,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    row_count=0,
                    rows=[],
                    columns=[],
                )

            except self._psycopg2.Error as e:
                error_msg = str(e)
                pgcode = getattr(e, 'pgcode', '')

                if pgcode == '42501':  # permission denied
                    return ExecutionResult(
                        success=False,
                        error=error_msg,
                        error_category=SQLValidationErrorCategory.PERMISSION_DENIED,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        row_count=0,
                        rows=[],
                        columns=[],
                    )

                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    error_category=SQLValidationErrorCategory.EXECUTION_ERROR,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    row_count=0,
                    rows=[],
                    columns=[],
                )

    def execute_async(
        self,
        sql: str,
        callback: Callable[[ExecutionResult], None],
        timeout_ms: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Execute SQL asynchronously.

        Args:
            sql: SQL to execute
            callback: Callback with result
            timeout_ms: Timeout in milliseconds
            params: Query parameters

        Returns:
            Query ID for cancellation
        """
        import asyncio
        query_id = str(uuid.uuid4())
        timeout_ms = timeout_ms or self._config.timeout_ms

        def execute():
            result = self.execute_sync(sql, timeout_ms, params)
            callback(result)

        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()

        return query_id

    def cancel(self, query_id: str) -> bool:
        """Cancel a running query.

        Args:
            query_id: Query ID to cancel

        Returns:
            True if cancelled
        """
        # PostgreSQL supports query cancellation via PID
        # This would need to track PIDs per query_id
        logger.warning(f"Query cancellation requested for {query_id}")
        return False

    def health_check(self) -> bool:
        """Check executor health.

        Returns:
            True if healthy
        """
        try:
            if self._conn:
                with self._conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return True
        except Exception:
            pass
        return False


def create_executor(
    executor_type: str = "duckdb",
    **kwargs: Any,
) -> ExecutorProvider:
    """Create an executor provider.

    Args:
        executor_type: Type of executor ("duckdb" or "postgresql")
        **kwargs: Executor-specific arguments

    Returns:
        Executor provider
    """
    if executor_type == "duckdb":
        return DuckDBExecutor(
            database=kwargs.get("database", ":memory:"),
            config=kwargs.get("config"),
        )
    elif executor_type == "postgresql":
        return PostgreSQLExecutor(
            host=kwargs.get("host", "localhost"),
            port=kwargs.get("port", 5432),
            database=kwargs.get("database", "postgres"),
            user=kwargs.get("user"),
            password=kwargs.get("password"),
            config=kwargs.get("config"),
        )
    else:
        raise ValueError(f"Unknown executor type: {executor_type}")
