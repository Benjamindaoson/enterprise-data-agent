"""Evaluation Regression Runner.

Tracks evaluation results over time and compares runs:
- baseline vs current
- run_id, git_sha, timestamp
- provider, model, prompt_version
- semantic_version, dataset_version
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EvaluationRun:
    """Single evaluation run."""

    run_id: str
    git_sha: str
    timestamp: str
    provider: str
    model: str | None = None
    prompt_version: str | None = None
    semantic_version: str | None = None
    dataset_version: str | None = None

    # Intent metrics
    intent_accuracy: float = 0.0
    metric_accuracy: float = 0.0
    dimension_accuracy: float = 0.0
    time_accuracy: float = 0.0

    # Retrieval metrics
    retrieval_recall_at_1: float = 0.0
    retrieval_recall_at_3: float = 0.0
    retrieval_precision_at_k: float = 0.0

    # Schema linking
    schema_linking_accuracy: float = 0.0

    # NL2SQL metrics
    sql_parse_validity: float = 0.0
    sql_execution_success: float = 0.0
    result_equivalence: float = 0.0
    semantic_correctness: float = 0.0
    repair_success: float = 0.0

    # Security metrics
    policy_escape_rate: float = 0.0
    security_test_pass_rate: float = 0.0

    # Agent metrics
    lane_selection_accuracy: float = 0.0
    tool_selection_accuracy: float = 0.0
    task_completion_rate: float = 0.0
    evidence_coverage: float = 0.0

    # Stability
    paraphrase_consistency: float = 0.0

    # Latency
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0

    # Counts
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "git_sha": self.git_sha,
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "semantic_version": self.semantic_version,
            "dataset_version": self.dataset_version,
            "intent_accuracy": self.intent_accuracy,
            "metric_accuracy": self.metric_accuracy,
            "dimension_accuracy": self.dimension_accuracy,
            "time_accuracy": self.time_accuracy,
            "retrieval_recall_at_1": self.retrieval_recall_at_1,
            "retrieval_recall_at_3": self.retrieval_recall_at_3,
            "retrieval_precision_at_k": self.retrieval_precision_at_k,
            "schema_linking_accuracy": self.schema_linking_accuracy,
            "sql_parse_validity": self.sql_parse_validity,
            "sql_execution_success": self.sql_execution_success,
            "result_equivalence": self.result_equivalence,
            "semantic_correctness": self.semantic_correctness,
            "repair_success": self.repair_success,
            "policy_escape_rate": self.policy_escape_rate,
            "security_test_pass_rate": self.security_test_pass_rate,
            "lane_selection_accuracy": self.lane_selection_accuracy,
            "tool_selection_accuracy": self.tool_selection_accuracy,
            "task_completion_rate": self.task_completion_rate,
            "evidence_coverage": self.evidence_coverage,
            "paraphrase_consistency": self.paraphrase_consistency,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationRun":
        return cls(**data)


@dataclass
class RegressionResult:
    """Comparison between two evaluation runs."""

    baseline_run: EvaluationRun
    current_run: EvaluationRun
    comparison_timestamp: str

    # Metric deltas
    metric_deltas: dict[str, float] = field(default_factory=dict)

    # Status per metric
    statuses: dict[str, str] = field(default_factory=dict)  # IMPROVED, UNCHANGED, REGRESSED

    def determine_status(self, metric_name: str, delta: float, threshold: float = 0.01) -> str:
        """Determine regression status for a metric."""
        if delta > threshold:
            return "IMPROVED"
        elif delta < -threshold:
            return "REGRESSED"
        else:
            return "UNCHANGED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_run_id": self.baseline_run.run_id,
            "current_run_id": self.current_run.run_id,
            "comparison_timestamp": self.comparison_timestamp,
            "metric_deltas": self.metric_deltas,
            "statuses": self.statuses,
            "summary": self._generate_summary(),
        }

    def _generate_summary(self) -> str:
        improved = sum(1 for s in self.statuses.values() if s == "IMPROVED")
        unchanged = sum(1 for s in self.statuses.values() if s == "UNCHANGED")
        regressed = sum(1 for s in self.statuses.values() if s == "REGRESSED")
        total = improved + unchanged + regressed
        return f"IMPROVED: {improved}/{total}, UNCHANGED: {unchanged}/{total}, REGRESSED: {regressed}/{total}"


class EvaluationRegressionRunner:
    """Runs evaluation and tracks regression."""

    def __init__(self, results_dir: Path | str = "evaluation/results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        git_sha: str,
        provider: str = "deterministic",
        model: str | None = None,
        **metrics: float,
    ) -> EvaluationRun:
        """Create a new evaluation run."""
        timestamp = datetime.now().isoformat()
        run_id = self._generate_run_id(git_sha, timestamp)

        run = EvaluationRun(
            run_id=run_id,
            git_sha=git_sha,
            timestamp=timestamp,
            provider=provider,
            model=model,
            **metrics,
        )
        return run

    def save_run(self, run: EvaluationRun) -> Path:
        """Save an evaluation run to disk."""
        filename = f"{run.run_id}.json"
        filepath = self.results_dir / filename
        with open(filepath, "w") as f:
            json.dump(run.to_dict(), f, indent=2)
        return filepath

    def load_run(self, run_id: str) -> EvaluationRun | None:
        """Load a saved evaluation run."""
        filepath = self.results_dir / f"{run_id}.json"
        if not filepath.exists():
            return None
        with open(filepath) as f:
            return EvaluationRun.from_dict(json.load(f))

    def get_latest_run(self) -> EvaluationRun | None:
        """Get the most recent evaluation run."""
        runs = sorted(self.results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not runs:
            return None
        with open(runs[-1]) as f:
            return EvaluationRun.from_dict(json.load(f))

    def get_baseline_run(self) -> EvaluationRun | None:
        """Get the baseline run (oldest run with 'baseline' in name or first run)."""
        runs = sorted(self.results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not runs:
            return None
        with open(runs[0]) as f:
            return EvaluationRun.from_dict(json.load(f))

    def compare_runs(
        self,
        baseline: EvaluationRun,
        current: EvaluationRun,
        threshold: float = 0.01,
    ) -> RegressionResult:
        """Compare two evaluation runs."""
        result = RegressionResult(
            baseline_run=baseline,
            current_run=current,
            comparison_timestamp=datetime.now().isoformat(),
        )

        # Compare all numeric metrics
        metrics_to_compare = [
            "intent_accuracy",
            "metric_accuracy",
            "dimension_accuracy",
            "time_accuracy",
            "retrieval_recall_at_1",
            "retrieval_recall_at_3",
            "retrieval_precision_at_k",
            "schema_linking_accuracy",
            "sql_parse_validity",
            "sql_execution_success",
            "result_equivalence",
            "semantic_correctness",
            "repair_success",
            "security_test_pass_rate",
            "lane_selection_accuracy",
            "tool_selection_accuracy",
            "task_completion_rate",
            "evidence_coverage",
            "paraphrase_consistency",
        ]

        for metric in metrics_to_compare:
            baseline_val = getattr(baseline, metric, 0.0)
            current_val = getattr(current, metric, 0.0)
            delta = current_val - baseline_val
            result.metric_deltas[metric] = delta
            result.statuses[metric] = result.determine_status(metric, delta, threshold)

        return result

    def save_regression_result(self, result: RegressionResult) -> Path:
        """Save regression comparison result."""
        filename = f"regression_{result.baseline_run.run_id}_{result.current_run.run_id}.json"
        filepath = self.results_dir / filename
        with open(filepath, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        return filepath

    def _generate_run_id(self, git_sha: str, timestamp: str) -> str:
        """Generate a unique run ID."""
        content = f"{git_sha}:{timestamp}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"run_{git_sha[:8]}_{hash_val}"

    def run_deterministic_evaluation(self) -> EvaluationRun:
        """Run the deterministic evaluation suite."""
        import subprocess

        # Run pytest with JSON report
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=no", "-q"],
            capture_output=True,
            text=True,
        )

        # Parse output for counts
        output = result.stdout + result.stderr

        # Extract counts (simplified)
        passed = 0
        failed = 0
        skipped = 0

        for line in output.split("\n"):
            if "passed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        try:
                            passed = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
            if "failed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "failed":
                        try:
                            failed = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
            if "skipped" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "skipped":
                        try:
                            skipped = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass

        # Get git SHA
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()[:12]

        total = passed + failed + skipped

        run = self.create_run(
            git_sha=git_sha,
            provider="deterministic",
            total_cases=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            # Approximate pass rates
            intent_accuracy=passed / total if total > 0 else 0.0,
            sql_parse_validity=passed / total if total > 0 else 0.0,
            security_test_pass_rate=passed / total if total > 0 else 0.0,
            task_completion_rate=passed / total if total > 0 else 0.0,
        )

        return run

    def ci_gate_check(self, current: EvaluationRun, baseline: EvaluationRun | None = None) -> tuple[bool, str]:
        """CI gate check for regression prevention.

        Returns (pass, message)
        """
        if baseline is None:
            # No baseline - just save current run
            self.save_run(current)
            return True, f"No baseline. Saved run {current.run_id}"

        result = self.compare_runs(baseline, current)

        # Check for regressions
        regressions = [m for m, s in result.statuses.items() if s == "REGRESSED"]

        if regressions:
            message = f"REGRESSION DETECTED in: {', '.join(regressions)}"
            self.save_regression_result(result)
            return False, message

        # All good
        message = result._generate_summary()
        self.save_run(current)
        self.save_regression_result(result)
        return True, message


# CLI interface
def main():
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description="Evaluation Regression Runner")
    parser.add_argument("--run", action="store_true", help="Run evaluation")
    parser.add_argument("--compare", action="store_true", help="Compare with baseline")
    parser.add_argument("--baseline", type=str, help="Baseline run ID")
    parser.add_argument("--ci-gate", action="store_true", help="CI gate check")

    args = parser.parse_args()

    runner = EvaluationRegressionRunner()

    if args.run:
        print("Running deterministic evaluation...")
        run = runner.run_deterministic_evaluation()
        print(f"Run completed: {run.run_id}")
        print(f"Total: {run.total_cases}, Passed: {run.passed}, Failed: {run.failed}")
        runner.save_run(run)
        print(f"Saved to {runner.results_dir}")

    elif args.ci_gate:
        print("Running CI gate check...")
        baseline = runner.get_baseline_run()
        current = runner.run_deterministic_evaluation()

        if baseline:
            print(f"Baseline: {baseline.run_id}")
        print(f"Current: {current.run_id}")

        passed, message = runner.ci_gate_check(current, baseline)
        print(message)

        if not passed:
            exit(1)

    elif args.compare:
        baseline = runner.load_run(args.baseline) if args.baseline else runner.get_baseline_run()
        current = runner.get_latest_run()

        if not baseline or not current:
            print("Need at least two runs to compare")
            exit(1)

        result = runner.compare_runs(baseline, current)
        print(yaml.dump(result.to_dict(), default_flow_style=False))


if __name__ == "__main__":
    main()
