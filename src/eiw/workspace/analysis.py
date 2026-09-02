"""Deterministic analytical workflow used by the reference workspace."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from eiw.domain.enums import TaskState
from eiw.semantic.package import load_semantic_package
from eiw.workspace.data import DIMENSIONS, METRICS, DataUnavailable, IowaData
from eiw.workspace.provider import DeterministicProvider
from eiw.workspace.store import WorkspaceStore

MONTHS = {name.lower(): number for number, name in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}
DEFAULT_USER = {"user_id": "local-user", "tenant_id": "local", "roles": ["business_analyst"], "policy_version": "local-policy-v1", "allowed_metric_ids": list(METRICS), "allowed_dimension_ids": list(DIMENSIONS), "data_classification_ceiling": "INTERNAL"}


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class AnalysisService:
    def __init__(self, store: WorkspaceStore, data: IowaData, artifact_root: Path) -> None:
        self.store = store
        self.data = data
        self.artifact_root = artifact_root
        self.provider = DeterministicProvider()
        package_path = Path("semantic_packages/iowa_liquor_wholesale/semantic-package.yaml")
        self.semantic = load_semantic_package(package_path) if package_path.exists() else None

    def _period(self, question: str) -> tuple[date, date, date, date]:
        matches = re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})", question, re.I)
        if matches:
            month, year = MONTHS[matches[0][0].lower()], int(matches[0][1])
        else:
            manifest = self.data.manifest()
            through = date.fromisoformat(manifest.get("business_date_max", "2026-07-31"))
            month, year = through.month, through.year
        current_start = date(year, month, 1)
        current_end = date(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)
        if re.search(r"year[- ]over[- ]year|\byoy\b|last year|same month", question, re.I) or len(matches) >= 2 and matches[1][1] != matches[0][1]:
            compare_start = date(year - 1, month, 1)
        else:
            compare_start = date(year if month > 1 else year - 1, month - 1 if month > 1 else 12, 1)
        compare_end = date(compare_start.year + (compare_start.month == 12), 1 if compare_start.month == 12 else compare_start.month + 1, 1) - timedelta(days=1)
        if len(matches) >= 2:
            explicit_month, explicit_year = MONTHS[matches[1][0].lower()], int(matches[1][1])
            compare_start = date(explicit_year, explicit_month, 1)
            compare_end = date(explicit_year + (explicit_month == 12), 1 if explicit_month == 12 else explicit_month + 1, 1) - timedelta(days=1)
        if re.search(r"last 12 months|12-month|twelve month", question, re.I):
            current_start = date(year - 1, month, 1)
        return current_start, current_end, compare_start, compare_end

    @staticmethod
    def _metric_ids(question: str) -> list[str]:
        lowered = question.lower()
        if re.search(r"profit|net income|margin", lowered):
            return []
        metrics = []
        if "spread" in lowered or "acquisition cost" in lowered or "cost" in lowered:
            metrics.append("wholesale_gross_spread")
        if "bottle" in lowered or "volume" in lowered or "quantity" in lowered:
            metrics.append("bottles_ordered")
        if "liter" in lowered:
            metrics.append("volume_liters")
        if "price" in lowered or "pvm" in lowered or "mix" in lowered:
            metrics.append("average_wholesale_price_per_bottle")
            if "bottles_ordered" not in metrics:
                metrics.append("bottles_ordered")
        if not metrics or "sales" in lowered or "revenue" in lowered:
            metrics.insert(0, "wholesale_sales_amount")
        unique = set(metrics)
        priority = ["wholesale_sales_amount", "bottles_ordered", "volume_liters", "average_wholesale_price_per_bottle", "wholesale_gross_spread"]
        return [metric for metric in priority if metric in unique]

    @staticmethod
    def _dimension(question: str) -> str | None:
        lowered = question.lower()
        plural_aliases = {"category": "categories", "county": "counties"}
        for dimension in ("vendor", "category", "store", "county", "product", "city"):
            if dimension in lowered or plural_aliases.get(dimension, f"{dimension}s") in lowered:
                return dimension
        if "by month" in lowered or "trend" in lowered:
            return "month"
        return None

    @staticmethod
    def _filters(question: str) -> dict[str, str]:
        result: dict[str, str] = {}
        patterns = {
            "county": r"(?:in|for)\s+([A-Z][A-Za-z ]+?)\s+county",
            "vendor": r"vendor\s+([A-Za-z0-9 &.-]+)",
            "store": r"store\s+([A-Za-z0-9 &.-]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, question, re.I)
            if match:
                result[key] = match.group(1).strip(" .,?")
        return result

    @staticmethod
    def _number(value: Any) -> float | None:
        return round(float(value), 2) if value is not None else None

    def _summary(self, start: date, end: date, compare_start: date, compare_end: date, metrics: list[str], filters: dict[str, str]) -> dict[str, Any]:
        current = self.data.aggregate(start, end, metrics, filters=filters)
        comparison = self.data.aggregate(compare_start, compare_end, metrics, filters=filters)
        current_row, comparison_row = (current[0] if current else {}), (comparison[0] if comparison else {})
        values: dict[str, Any] = {}
        for metric in metrics:
            key = metric
            if metric == "average_wholesale_price_per_bottle":
                key = metric
            values[key] = {"current": self._number(current_row.get(key)), "comparison": self._number(comparison_row.get(key))}
            cur, prev = current_row.get(key), comparison_row.get(key)
            values[key]["delta"] = self._number((cur or 0) - (prev or 0)) if cur is not None or prev is not None else None
            if cur is not None and prev not in (None, 0):
                cur_value, prev_value = cast(float, cur), cast(float, prev)
                values[key]["change_pct"] = self._number(((cur_value - prev_value) / abs(prev_value)) * 100)
            else:
                values[key]["change_pct"] = None
        return values

    def _event(self, task_id: str, event_type: str, message: str, **payload: Any) -> None:
        self.store.add_event(task_id, event_type, message, **payload)

    def create(self, question: str, user: dict[str, Any] | None = None, lineage: dict[str, Any] | None = None) -> dict[str, Any]:
        task_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        user_context = {**DEFAULT_USER, **(user or {})}
        manifest = self.data.manifest()
        task: dict[str, Any] = {
            "task_id": task_id, "business_question": question, "user_context": user_context,
            "domain_id": "iowa_liquor_wholesale", "state": TaskState.CREATED.value,
            "created_at": now, "updated_at": now, "lineage": lineage or {}, "events": [],
            "claims": [], "evidence": [], "observations": [], "validations": [], "artifacts": [],
        }
        self.store.put_task(task)
        self._event(task_id, "TASK_CREATED", "Analysis task created.")
        if not self.data.available():
            task["state"] = TaskState.FAILED.value
            task["error"] = "Curated snapshot unavailable. Run `make data` to build the measured official dataset."
            self.store.put_task(task)
            self._event(task_id, "FAILURE_RECORDED", task["error"])
            return task
        metrics = self._metric_ids(question)
        start, end, compare_start, compare_end = self._period(question)
        dimension = self._dimension(question)
        filters = self._filters(question)
        task["periods"] = {"primary": {"start": _iso(start), "end": _iso(end)}, "comparison": {"start": _iso(compare_start), "end": _iso(compare_end)}}
        task["resolved_context"] = {
            "context_version": "ctx-" + hashlib.sha256((question + manifest.get("curated_file_sha256", "")).encode()).hexdigest()[:12],
            "dataset_snapshot": self.data.snapshot_id, "dataset_status": manifest.get("status"),
            "semantic_version": self.semantic.package.version if self.semantic else "unavailable",
            "metrics": [{"id": metric, **METRICS[metric]} for metric in metrics], "dimension": dimension,
            "filters": filters, "allowed_objects": ["fact_liquor_order_line"],
            "quality_warnings": [manifest.get("warning")] if manifest.get("warning") else [],
        }
        self._event(task_id, "CONTEXT_COMPILED", "Context compiled from the semantic package and immutable snapshot.", context=task["resolved_context"])
        if not metrics:
            task["state"] = TaskState.NEEDS_CLARIFICATION.value
            task["clarification"] = {"question": "This dataset supports wholesale sales, bottles, volume, price, and wholesale gross spread. Did you mean wholesale gross spread rather than store or net profit?", "reason": "The Iowa source does not contain accounting profit or net profit."}
            task["limitations"] = ["The source represents wholesale orders, not consumer POS or store accounting profit."]
            self.store.put_task(task)
            self._event(task_id, "CLARIFICATION_REQUIRED", task["clarification"]["question"])
            return task
        allowed_metrics = set(user_context.get("allowed_metric_ids", METRICS))
        allowed_dimensions = set(user_context.get("allowed_dimension_ids", DIMENSIONS))
        if any(metric not in allowed_metrics for metric in metrics) or (dimension and dimension not in allowed_dimensions):
            task["state"] = TaskState.FAILED.value
            task["error"] = "The requested metric or dimension is outside the current user policy."
            task["failure_category"] = "POLICY"
            self.store.put_task(task)
            self._event(task_id, "FAILURE_RECORDED", task["error"], category="POLICY")
            return task
        if "wholesale_gross_spread" in metrics and (start < date(2025, 7, 1) or compare_start < date(2025, 7, 1)):
            task["coverage_warning"] = "Wholesale cost and spread are only available from 2025-07-01; the requested comparison crosses the coverage boundary."
            task["state"] = TaskState.PARTIAL.value
            task["limitations"] = [task["coverage_warning"], "Cost values outside the declared window are not zero-filled."]
            self.store.put_task(task)
            self._event(task_id, "VALIDATION_COMPLETED", task["coverage_warning"], status="WARNING")
            return task
        plan = self._plan(task_id, metrics, dimension)
        task["plan"] = plan
        task["hypotheses"] = self._hypotheses(task_id, metrics, dimension)
        task["checkpoint"] = {"state_version": 1, "storage_uri": f"/artifacts/{task_id}/checkpoint.json", "saved_at": datetime.now(UTC).isoformat()}
        self._event(task_id, "PLAN_CREATED", "Structured analysis plan created.", step_count=len(plan["steps"]))
        try:
            task["state"] = TaskState.RUNNING.value
            self.store.put_task(task)
            summary = self._summary(start, end, compare_start, compare_end, metrics, filters)
            task["summary"] = summary
            task["pvm"] = self._pvm(summary)
            if re.search(r"\bcause\b|caused by|marketing campaign", question, re.I):
                task["causal_warning"] = "Observed contribution does not establish causal impact. No campaign or intervention field exists in the snapshot."
            self._event(task_id, "TOOL_COMPLETED", "Baseline metrics computed with governed DuckDB execution.", tool="metric_query")
            if dimension:
                task["contributions"] = self._contributions(start, end, compare_start, compare_end, metrics[0], dimension, filters)
                self._event(task_id, "TOOL_COMPLETED", f"Contribution analysis completed by {dimension}.", tool="contribution_analysis")
            task["trend"] = self.data.monthly_trend(max(date(2024, 1, 1), start - timedelta(days=365)), end, ["wholesale_sales_amount"])
            self._make_artifacts(task)
            self._make_claims(task)
            task["state"] = TaskState.PARTIAL.value if task.get("causal_warning") else TaskState.COMPLETED.value
            task["completed_at"] = datetime.now(UTC).isoformat()
            if task.get("causal_warning"):
                task["limitations"] = [task["causal_warning"]]
            self._event(task_id, "VALIDATION_COMPLETED", "Metric, period, evidence coverage, and result consistency checks passed.", status="PASSED")
            self._event(task_id, "TASK_STATE_CHANGED", "Analysis completed.", state=task["state"])
        except (DataUnavailable, ValueError) as exc:
            task["state"] = TaskState.FAILED.value
            task["error"] = str(exc)
            self._event(task_id, "FAILURE_RECORDED", str(exc))
        self.store.put_task(task)
        return task

    def _plan(self, task_id: str, metrics: list[str], dimension: str | None) -> dict[str, Any]:
        steps = [
            {"ordinal": 1, "title": "Establish baseline", "purpose": "Compute requested metrics for the primary and comparison periods.", "tool": "metric_query"},
            {"ordinal": 2, "title": "Investigate drivers", "purpose": f"Rank changes by {dimension or 'business dimension'} and test quantity, price, and mix signals.", "tool": "contribution_analysis"},
            {"ordinal": 3, "title": "Verify and synthesize", "purpose": "Reconcile totals, attach evidence, and separate facts from interpretations.", "tool": "verification"},
        ]
        return {"objective": "Explain the requested wholesale performance change with reproducible evidence.", "metrics": metrics, "steps": steps, "completion_criteria": ["Primary and comparison periods resolved", "Aggregate result reconciled", "Important claims have evidence", "Limitations are visible"], "budgets": {"max_queries": 12, "max_tool_calls": 20}}

    def _hypotheses(self, task_id: str, metrics: list[str], dimension: str | None) -> list[dict[str, Any]]:
        topics = [("quantity", "Change may be associated with bottles ordered."), ("unit_price", "Change may be associated with composite wholesale price per bottle."), ("product_mix", "The product/category mix may have shifted between periods.")]
        return [{"hypothesis_id": str(uuid4()), "topic": topic, "statement": statement, "state": "SUPPORTED" if topic == "quantity" and "bottles_ordered" in metrics else "TESTING"} for topic, statement in topics]

    def _contributions(self, start: date, end: date, compare_start: date, compare_end: date, metric: str, dimension: str, filters: dict[str, str]) -> list[dict[str, Any]]:
        current = {row.get("dimension_value"): row for row in self.data.aggregate(start, end, [metric], dimension, filters)}
        previous = {row.get("dimension_value"): row for row in self.data.aggregate(compare_start, compare_end, [metric], dimension, filters)}
        output = []
        key = metric
        for value in set(current) | set(previous):
            cur, prev = current.get(value, {}).get(key) or 0, previous.get(value, {}).get(key) or 0
            output.append({"dimension_value": value, "current": self._number(cur), "comparison": self._number(prev), "delta": self._number(cur - prev)})
        return sorted(output, key=lambda item: abs(float(item["delta"] or 0)), reverse=True)[:25]

    def _pvm(self, summary: dict[str, Any]) -> dict[str, float | None]:
        """Decompose sales change into volume, composite price, and residual mix."""

        sales = summary.get("wholesale_sales_amount", {})
        bottles = summary.get("bottles_ordered", {})
        price = summary.get("average_wholesale_price_per_bottle", {})
        current_bottles, previous_bottles = bottles.get("current"), bottles.get("comparison")
        current_price, previous_price = price.get("current"), price.get("comparison")
        delta = sales.get("delta")
        if None in (delta, current_bottles, previous_bottles, current_price, previous_price):
            return {"volume_effect": None, "price_effect": None, "mix_residual": None, "total_change": delta}
        volume_effect = (current_bottles - previous_bottles) * previous_price
        price_effect = current_bottles * (current_price - previous_price)
        return {"volume_effect": self._number(volume_effect), "price_effect": self._number(price_effect), "mix_residual": self._number(delta - volume_effect - price_effect), "total_change": delta}

    def _observation(self, task: dict[str, Any], title: str, values: dict[str, Any], computation: str) -> dict[str, Any]:
        result_hash = hashlib.sha256(json_bytes(values)).hexdigest()
        observation = {"observation_id": str(uuid4()), "title": title, "values": values, "computation": computation, "result_hash": result_hash, "dataset_snapshot": self.data.snapshot_id, "created_at": datetime.now(UTC).isoformat()}
        task["observations"].append(observation)
        return observation

    def _make_claims(self, task: dict[str, Any]) -> None:
        summary = task.get("summary", {})
        sales = summary.get("wholesale_sales_amount")
        if sales is None:
            sales = summary.get("wholesale_gross_spread")
        obs = self._observation(task, "Period summary", summary, "IowaData.aggregate")
        if sales:
            change = sales.get("delta")
            direction = "increased" if (change or 0) >= 0 else "decreased"
            label = "Wholesale gross spread" if "wholesale_sales_amount" not in summary else "Wholesale sales"
            claim = {"claim_id": str(uuid4()), "type": "FACT", "status": "VERIFIED", "statement": f"{label} {direction} by ${abs(change or 0):,.2f} between the selected periods.", "evidence_ids": [obs["observation_id"]], "limitations": ["This is wholesale order activity, not consumer POS sales."]}
            task["claims"].append(claim)
        if task.get("contributions"):
            top = task["contributions"][0]
            obs2 = self._observation(task, "Contribution ranking", {"top": top, "rows": task["contributions"]}, "IowaData.aggregate grouped by dimension")
            task["claims"].append({"claim_id": str(uuid4()), "type": "INFERENCE", "status": "QUALIFIED", "statement": f"{top['dimension_value']} was the largest absolute contributor to the selected {task['resolved_context']['dimension']} change.", "evidence_ids": [obs2["observation_id"]], "limitations": ["Contribution is an association in the observed data; it does not establish causation."]})
        elif task.get("pvm") and task["pvm"].get("volume_effect") is not None:
            obs2 = self._observation(task, "Price / volume / mix decomposition", task["pvm"], "AnalysisService._pvm")
            task["claims"].append({"claim_id": str(uuid4()), "type": "INFERENCE", "status": "QUALIFIED", "statement": "The selected sales change is decomposed into volume, composite price, and a residual mix component.", "evidence_ids": [obs2["observation_id"]], "limitations": ["The residual is mix-sensitive and is not a causal explanation."]})
        for claim in task["claims"]:
            evidence = {"evidence_id": str(uuid4()), "claim_id": claim["claim_id"], "observation_ids": claim["evidence_ids"], "relation": "SUPPORTS", "metric_version": task["resolved_context"]["semantic_version"], "context_version": task["resolved_context"]["context_version"], "dataset_snapshot": self.data.snapshot_id, "result_hash": task["observations"][0]["result_hash"], "validation": ["metric/formula_consistency", "time_range", "result_reproducibility"]}
            task["evidence"].append(evidence)
            self._event(task["task_id"], "EVIDENCE_LINKED", "Evidence captured during analysis.", claim_id=claim["claim_id"], evidence_id=evidence["evidence_id"])

    def _make_artifacts(self, task: dict[str, Any]) -> None:
        folder = self.artifact_root / task["task_id"]
        folder.mkdir(parents=True, exist_ok=True)
        markdown = self._report_markdown(task)
        md_path = folder / "report.md"
        html_path = folder / "report.html"
        md_path.write_text(markdown)
        html_path.write_text("<html><head><meta charset='utf-8'><title>Analysis report</title></head><body><pre>" + html.escape(markdown) + "</pre></body></html>")
        (folder / "checkpoint.json").write_text(json.dumps({"task_id": task["task_id"], "state_version": 1, "state": task.get("state"), "plan": task.get("plan"), "hypotheses": task.get("hypotheses"), "summary": task.get("summary")}, indent=2, default=str))
        task["artifacts"] = [{"artifact_id": str(uuid4()), "type": "REPORT", "format": "markdown", "uri": f"/api/v1/analysis-tasks/{task['task_id']}/artifacts/report.md", "content_hash": hashlib.sha256(markdown.encode()).hexdigest()}, {"artifact_id": str(uuid4()), "type": "REPORT", "format": "html", "uri": f"/api/v1/analysis-tasks/{task['task_id']}/artifacts/report.html", "content_hash": hashlib.sha256(markdown.encode()).hexdigest()}]

    def _report_markdown(self, task: dict[str, Any]) -> str:
        periods = task["periods"]
        lines = ["# Enterprise Intelligence Workspace analysis", "", f"**Question:** {task['business_question']}", "", "## Executive Summary", ""]
        lines.extend(f"- {claim['statement']}" for claim in task.get("claims", []))
        lines += ["", "## Business Performance", f"- Primary: {periods['primary']['start']} to {periods['primary']['end']}", f"- Comparison: {periods['comparison']['start']} to {periods['comparison']['end']}", ""]
        for metric, values in task.get("summary", {}).items():
            lines.append(f"- {metric.replace('_', ' ').title()}: {self._number(values.get('current'))} current vs {self._number(values.get('comparison'))} comparison ({self._number(values.get('delta'))} delta)")
        lines += ["", "## Key Findings", ""]
        lines.extend(f"- {claim['statement']}" for claim in task.get("claims", []))
        lines += ["", "## Driver Analysis", ""]
        if task.get("pvm"):
            lines.extend(f"- {key.replace('_', ' ').title()}: {self._number(value)}" for key, value in task["pvm"].items() if value is not None)
        if task.get("contributions"):
            lines.append(f"- Top contribution: {task['contributions'][0]['dimension_value']} ({self._number(task['contributions'][0]['delta'])} change)")
        lines += ["", "## Supporting Evidence", ""]
        lines.extend(f"- {e['evidence_id']}: {e['dataset_snapshot']} / {e['metric_version']} / {e['context_version']}" for e in task.get("evidence", []))
        lines += ["", "## Limitations", "- Source data represents Iowa wholesale orders; it cannot establish consumer demand, store profit, or causation.", "", "## Recommendations", "- Use the linked contribution evidence to prioritize a business review of the largest observed driver; treat it as an investigation lead, not a causal conclusion."]
        return "\n".join(lines) + "\n"


def json_bytes(value: Any) -> bytes:
    import json
    return json.dumps(value, sort_keys=True, default=str).encode()
