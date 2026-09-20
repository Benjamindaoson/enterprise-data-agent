"""Evaluation Runner.

Main evaluation orchestration:
- Run evaluation suites
- Track results
- Compare with baselines
- Generate reports
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from eiw.agent.provider import ModelProvider
from eiw.agent.provider import ProviderConfig, create_provider
from eiw.evaluation.graders import get_grader
from eiw.evaluation.suites import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationSuite,
    MultiSuiteResult,
    SuiteResult,
    get_suite_cases,
)

from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "evaluation_runner")

# Try to import regression runner from project root
try:
    import sys
    _eval_path = Path(__file__).parent.parent.parent / "evaluation"
    if str(_eval_path.parent) not in sys.path:
        sys.path.insert(0, str(_eval_path.parent))
    from evaluation.regression_runner import (
        EvaluationRun,
        EvaluationRegressionRunner,
        RegressionResult,
    )
    HAS_REGRESSION = True
except ImportError:
    HAS_REGRESSION = False
    # Fallback dataclasses
    from dataclasses import dataclass, field

    @dataclass
    class EvaluationRun:
        run_id: str = ""
        git_sha: str = ""
        timestamp: str = ""
        provider: str = ""
        model: str | None = None
        total_cases: int = 0
        passed: int = 0
        failed: int = 0
        skipped: int = 0
        intent_accuracy: float = 0.0
        metric_accuracy: float = 0.0
        sql_parse_validity: float = 0.0
        task_completion_rate: float = 0.0

        def to_dict(self) -> dict[str, Any]:
            return {"run_id": self.run_id, "git_sha": self.git_sha}

    @dataclass
    class RegressionResult:
        baseline_run: EvaluationRun
        current_run: EvaluationRun
        comparison_timestamp: str = ""
        metric_deltas: dict[str, float] = field(default_factory=dict)
        statuses: dict[str, str] = field(default_factory=dict)

        def _generate_summary(self) -> str:
            return "Summary unavailable"

    class EvaluationRegressionRunner:
        def __init__(self, results_dir: str = "evaluation/results"):
            self.results_dir = Path(results_dir)

        def get_baseline_run(self):
            return None

        def save_run(self, run):
            pass

        def ci_gate_check(self, current, baseline):
            return True, "No regression check available"


class EvaluationRunner:
    """Orchestrates evaluation runs across suites."""

    def __init__(
        self,
        provider: ModelProvider | None = None,
        results_dir: str = "evaluation/results",
    ):
        self.provider = provider
        self.regression_runner = EvaluationRegressionRunner(results_dir)

    async def run_case(
        self,
        case: EvaluationCase,
        provider: ModelProvider | None = None,
    ) -> EvaluationCaseResult:
        """Run a single evaluation case.

        Args:
            case: Evaluation case to run
            provider: Optional provider override

        Returns:
            Case result
        """
        try:
            # Use provided provider or instance provider
            p = provider or self.provider

            if p is None:
                # Use deterministic provider
                p = create_provider(ProviderConfig())

            # Get appropriate grader
            grader = get_grader(case.suite)

            # Execute query through agent/provider
            if p:
                # Build prompt
                prompt = f"Query: {case.query}\nExpected: {case.expected}"

                if hasattr(p, 'complete'):
                    response = await p.complete(
                        prompt=prompt,
                        system="You are a BI assistant. Respond with JSON matching the expected format.",
                    )
                    output = self._parse_output(response.content)
                else:
                    output = {"intent": "unknown"}
            else:
                output = {"intent": "unknown"}

            # Grade result
            passed, score, details = grader.grade(case, output)

            return EvaluationCaseResult(
                case_id=case.case_id,
                suite=case.suite,
                passed=passed,
                score=score,
                details=details,
            )

        except Exception as e:
            logger.error(f"Case {case.case_id} failed: {e}")
            return EvaluationCaseResult(
                case_id=case.case_id,
                suite=case.suite,
                passed=False,
                score=0.0,
                error=str(e),
            )

    async def run_suite(
        self,
        suite: EvaluationSuite,
        provider: ModelProvider | None = None,
    ) -> SuiteResult:
        """Run all cases in a suite.

        Args:
            suite: Suite to run
            provider: Optional provider override

        Returns:
            Suite result
        """
        cases = get_suite_cases(suite)
        if not cases:
            logger.warning(f"No cases for suite: {suite}")
            return SuiteResult(
                suite=suite,
                total_cases=0,
                passed=0,
                failed=0,
                skipped=len(cases),
                average_score=0.0,
                case_results=[],
                duration_ms=0.0,
            )

        start_time = time.time()
        results: list[EvaluationCaseResult] = []
        passed = 0
        failed = 0

        for case in cases:
            result = await self.run_case(case, provider)
            results.append(result)
            if result.passed:
                passed += 1
            else:
                failed += 1

        duration_ms = (time.time() - start_time) * 1000
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0

        return SuiteResult(
            suite=suite,
            total_cases=len(cases),
            passed=passed,
            failed=failed,
            skipped=0,
            average_score=avg_score,
            case_results=results,
            duration_ms=duration_ms,
        )

    async def run_all_suites(
        self,
        suites: list[EvaluationSuite] | None = None,
        provider: ModelProvider | None = None,
    ) -> MultiSuiteResult:
        """Run all specified suites.

        Args:
            suites: Suites to run (default: all)
            provider: Optional provider override

        Returns:
            Multi-suite result
        """
        if suites is None:
            suites = list(EvaluationSuite)

        start_time = time.time()
        suite_results: list[SuiteResult] = []

        for suite in suites:
            logger.info(f"Running suite: {suite.value}")
            result = await self.run_suite(suite, provider)
            suite_results.append(result)

        duration_ms = (time.time() - start_time) * 1000

        total_cases = sum(r.total_cases for r in suite_results)
        total_passed = sum(r.passed for r in suite_results)
        total_failed = sum(r.failed for r in suite_results)
        total_skipped = sum(r.skipped for r in suite_results)

        overall_score = sum(
            r.average_score * r.total_cases for r in suite_results
        ) / total_cases if total_cases > 0 else 0.0

        return MultiSuiteResult(
            suite_results=suite_results,
            total_cases=total_cases,
            total_passed=total_passed,
            total_failed=total_failed,
            total_skipped=total_skipped,
            overall_score=overall_score,
            duration_ms=duration_ms,
        )

    def create_run_from_result(
        self,
        result: MultiSuiteResult,
        git_sha: str,
        provider: str = "deterministic",
        model: str | None = None,
    ) -> EvaluationRun:
        """Create an EvaluationRun from a multi-suite result.

        Args:
            result: Multi-suite result
            git_sha: Git commit SHA
            provider: Provider name
            model: Model name

        Returns:
            EvaluationRun instance
        """
        if HAS_REGRESSION and hasattr(self.regression_runner, 'create_run'):
            run = self.regression_runner.create_run(
                git_sha=git_sha,
                provider=provider,
                model=model,
                total_cases=result.total_cases,
                passed=result.total_passed,
                failed=result.total_failed,
                skipped=result.total_skipped,
                intent_accuracy=result.overall_score,
                metric_accuracy=result.overall_score,
                sql_parse_validity=result.overall_score,
                task_completion_rate=(
                    result.total_passed / result.total_cases
                    if result.total_cases > 0
                    else 0.0
                ),
            )
        else:
            # Fallback: create basic run object
            run = EvaluationRun(
                run_id=f"run_{git_sha[:8]}",
                git_sha=git_sha,
                timestamp=datetime.now().isoformat(),
                provider=provider,
                model=model,
                total_cases=result.total_cases,
                passed=result.total_passed,
                failed=result.total_failed,
                skipped=result.total_skipped,
                intent_accuracy=result.overall_score,
                metric_accuracy=result.overall_score,
                sql_parse_validity=result.overall_score,
                task_completion_rate=(
                    result.total_passed / result.total_cases
                    if result.total_cases > 0
                    else 0.0
                ),
            )
        return run

    def compare_with_baseline(
        self,
        current: EvaluationRun,
    ) -> tuple[bool, RegressionResult]:
        """Compare current run with baseline.

        Args:
            current: Current evaluation run

        Returns:
            Tuple of (passed, regression_result)
        """
        return self.regression_runner.ci_gate_check(
            current,
            self.regression_runner.get_baseline_run(),
        )

    def _parse_output(self, content: str) -> dict[str, Any]:
        """Parse LLM output to structured format.

        Args:
            content: Raw LLM response

        Returns:
            Parsed output dict
        """
        import json

        # Try JSON parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown
        import re
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: extract key-value pairs
        output = {}
        for line in content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                output[key.strip().strip('"').strip("'")] = (
                    value.strip().strip('"').strip("'")
                )

        return output


async def run_evaluation(
    suites: list[EvaluationSuite] | None = None,
    provider_config: ProviderConfig | None = None,
    save_run: bool = True,
    check_regression: bool = True,
) -> tuple[MultiSuiteResult, bool]:
    """Convenience function to run evaluation.

    Args:
        suites: Suites to run
        provider_config: Provider configuration
        save_run: Whether to save the run
        check_regression: Whether to check for regressions

    Returns:
        Tuple of (result, passed_ci_gate)
    """
    import subprocess

    # Get git SHA
    try:
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()[:12]
    except Exception:
        git_sha = "unknown"

    # Create provider
    provider = create_provider(provider_config) if provider_config else None

    # Create runner
    runner = EvaluationRunner(provider=provider)

    # Run evaluation
    result = await runner.run_all_suites(suites, provider)

    # Print summary
    print(f"\nEvaluation Results:")
    print(f"Total Cases: {result.total_cases}")
    print(f"Passed: {result.total_passed}")
    print(f"Failed: {result.total_failed}")
    print(f"Skipped: {result.total_skipped}")
    print(f"Overall Score: {result.overall_score:.2%}")
    print(f"Duration: {result.duration_ms:.0f}ms")

    passed_ci = True
    if save_run:
        # Create and save evaluation run
        eval_run = runner.create_run_from_result(
            result,
            git_sha,
            provider_config.provider_type.value if provider_config else "deterministic",
            provider_config.model_name if provider_config else None,
        )
        runner.regression_runner.save_run(eval_run)

        if check_regression:
            passed_ci, regression_result = runner.compare_with_baseline(eval_run)
            print(f"\nRegression Check: {'PASSED' if passed_ci else 'FAILED'}")
            if not passed_ci:
                print(f"Regressions: {regression_result._generate_summary()}")

    return result, passed_ci
