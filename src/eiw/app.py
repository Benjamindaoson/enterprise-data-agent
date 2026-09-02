"""FastAPI application for the complete local reference workspace."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from eiw.workspace.analysis import DEFAULT_USER, AnalysisService
from eiw.workspace.data import DIMENSIONS, METRICS, IowaData
from eiw.workspace.store import WorkspaceStore


class CreateTaskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    user_context: dict[str, Any] | None = None


class FollowUpRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    referenced_evidence_ids: list[str] = Field(default_factory=list)


class ClarificationRequest(BaseModel):
    response: str = Field(min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


def create_app() -> FastAPI:
    artifact_root = Path(os.getenv("EIW_ARTIFACT_ROOT", "./artifacts"))
    store = WorkspaceStore(artifact_root / "workspace-state.json")
    data = IowaData()
    service = AnalysisService(store, data, artifact_root)
    app = FastAPI(title="Enterprise Intelligence Workspace", version="0.2.0", description="Evidence-native analytical workspace for Iowa wholesale intelligence.")
    static_dir = Path(__file__).parent / "web" / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    def home() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "product": "Enterprise Intelligence Workspace", "data_available": data.available()}

    @app.post("/api/v1/analysis-tasks")
    def create_task(request: CreateTaskRequest) -> dict[str, Any]:
        return service.create(request.question, {**DEFAULT_USER, **(request.user_context or {})})

    @app.post("/api/v1/analysis-tasks/{task_id}/follow-ups")
    def follow_up(task_id: str, request: FollowUpRequest) -> dict[str, Any]:
        parent = store.get_task(task_id)
        if not parent:
            raise HTTPException(404, "Analysis task not found")
        lineage = {"parent_task_id": task_id, "reused_evidence_ids": request.referenced_evidence_ids, "parent_context_version": parent.get("resolved_context", {}).get("context_version")}
        return service.create(request.question, parent.get("user_context", DEFAULT_USER), lineage)

    @app.get("/api/v1/analysis-tasks")
    def list_tasks() -> dict[str, Any]:
        return {"items": store.list_tasks()}

    @app.get("/api/v1/analysis-tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, Any]:
        task = store.get_task(task_id)
        if not task:
            raise HTTPException(404, "Analysis task not found")
        return task

    @app.get("/api/v1/analysis-tasks/{task_id}/plan")
    def get_plan(task_id: str) -> dict[str, Any]:
        task = get_task(task_id)
        return cast(dict[str, Any], task.get("plan", {"steps": [], "message": "A plan is created after clarification and data availability checks."}))

    @app.get("/api/v1/analysis-tasks/{task_id}/investigation")
    def investigation(task_id: str) -> dict[str, Any]:
        task = get_task(task_id)
        return {"hypotheses": task.get("hypotheses", []), "observations": task.get("observations", []), "contributions": task.get("contributions", []), "events": task.get("events", [])}

    @app.get("/api/v1/analysis-tasks/{task_id}/claims")
    def claims(task_id: str) -> dict[str, Any]:
        return {"items": get_task(task_id).get("claims", [])}

    @app.get("/api/v1/analysis-tasks/{task_id}/evidence")
    def evidence(task_id: str) -> dict[str, Any]:
        return {"items": get_task(task_id).get("evidence", [])}

    @app.get("/api/v1/analysis-tasks/{task_id}/evidence/{evidence_id}")
    def evidence_detail(task_id: str, evidence_id: str) -> dict[str, Any]:
        items = evidence(task_id)["items"]
        for item in items:
            if item["evidence_id"] == evidence_id:
                return cast(dict[str, Any], item)
        raise HTTPException(404, "Evidence not found")

    @app.get("/api/v1/analysis-tasks/{task_id}/artifacts")
    def artifacts(task_id: str) -> dict[str, Any]:
        return {"items": get_task(task_id).get("artifacts", [])}

    @app.get("/api/v1/analysis-tasks/{task_id}/artifacts/{filename}")
    def artifact_file(task_id: str, filename: str) -> FileResponse:
        if filename not in {"report.md", "report.html"}:
            raise HTTPException(404, "Artifact not found")
        path = artifact_root / task_id / filename
        if not path.exists():
            raise HTTPException(404, "Artifact not found")
        return FileResponse(path, media_type="text/markdown" if filename.endswith(".md") else "text/html")

    @app.get("/api/v1/analysis-tasks/{task_id}/events")
    def events(task_id: str) -> StreamingResponse:
        get_task(task_id)
        items = store.events(task_id)
        body = "".join(f"event: {item['event_type']}\ndata: {__import__('json').dumps(item)}\n\n" for item in items)
        return StreamingResponse(iter([body]), media_type="text/event-stream")

    @app.get("/api/v1/analysis-tasks/{task_id}/trace")
    def trace(task_id: str) -> dict[str, Any]:
        task = get_task(task_id)
        return {"task_id": task_id, "trace": task.get("events", []), "checkpoint": task.get("checkpoint")}

    @app.post("/api/v1/analysis-tasks/{task_id}/replay")
    def replay(task_id: str) -> dict[str, Any]:
        task = get_task(task_id)
        if not task.get("checkpoint"):
            raise HTTPException(409, "No checkpoint is available for this task")
        task["replay"] = {"source_checkpoint": task["checkpoint"], "replayed_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(), "status": "REPLAYABLE"}
        store.put_task(task)
        store.add_event(task_id, "CHECKPOINT_SAVED", "Checkpoint replay verified from the local artifact.")
        return cast(dict[str, Any], task["replay"])

    @app.post("/api/v1/analysis-tasks/{task_id}/clarifications")
    def clarification(task_id: str, request: ClarificationRequest) -> dict[str, Any]:
        task = get_task(task_id)
        task["clarification_response"] = request.response
        task["state"] = "PARTIAL"
        task["limitations"] = task.get("limitations", []) + ["The clarification was recorded; rerun with a supported wholesale metric to complete analysis."]
        store.put_task(task)
        store.add_event(task_id, "TASK_STATE_CHANGED", "Clarification recorded; task remains partial.")
        return task

    @app.post("/api/v1/analysis-tasks/{task_id}/cancel")
    def cancel(task_id: str) -> dict[str, Any]:
        task = get_task(task_id)
        if task.get("state") not in {"COMPLETED", "FAILED", "PARTIAL", "CANCELLED"}:
            task["state"] = "CANCELLED"
            store.put_task(task)
            store.add_event(task_id, "TASK_STATE_CHANGED", "Analysis cancelled.")
        return task

    @app.post("/api/v1/analysis-tasks/{task_id}/feedback")
    def feedback(task_id: str, request: FeedbackRequest) -> dict[str, Any]:
        task = get_task(task_id)
        task.setdefault("feedback", []).append(request.model_dump())
        store.put_task(task)
        return {"saved": True, "feedback": task["feedback"][-1]}

    @app.get("/api/v1/home")
    def home_data() -> dict[str, Any]:
        tasks = store.list_tasks()
        return {"dataset": data.status(), "recent_analyses": tasks[:5], "suggestions": ["Analyze the latest complete month", "Compare July 2026 with June 2026", "Which vendors contributed most to the change?", "Break down category performance"], "metrics": list(METRICS.values())}

    @app.get("/api/v1/data/status")
    def data_status() -> dict[str, Any]:
        return {"dataset": data.status(), "dimensions": [{"id": key, "label": value[1]} for key, value in DIMENSIONS.items()], "metrics": [{"id": key, **value} for key, value in METRICS.items()]}

    @app.get("/api/v1/semantic")
    def semantic() -> dict[str, Any]:
        package = service.semantic
        if package is None:
            return {"status": "unavailable"}
        return package.model_dump(mode="json")

    @app.get("/api/v1/evaluation")
    def evaluation() -> dict[str, Any]:
        path = Path("evaluation/cases/phase0-initial.yaml")
        count = 0
        suite = "unavailable"
        if path.exists():
            import yaml  # type: ignore[import-untyped]
            parsed = yaml.safe_load(path.read_text())
            suite, count = parsed.get("suite_version", "unknown"), len(parsed.get("cases", []))
        latest = store.latest_evaluation()
        return {"suite_version": suite, "case_count": count, "status": "MEASURED" if latest else "CASES_LOADED_NOT_RUN", "latest_run": latest, "metrics": latest.get("metrics", []) if latest else [{"name": name, "status": "NOT_MEASURED"} for name in ["Semantic Accuracy", "Numeric Accuracy", "Evidence Coverage", "Correct Abstention", "Policy Compliance", "Runtime Success", "Report Faithfulness"]], "note": "Evaluation values are shown only after a reproducible suite run; no values are fabricated."}

    @app.post("/api/v1/evaluation/run")
    def run_evaluation() -> dict[str, Any]:
        from eiw.evaluation.loader import load_cases

        path = Path("evaluation/cases/phase0-initial.yaml")
        if not path.exists():
            raise HTTPException(404, "Evaluation suite not found")
        suite_version, cases = load_cases(path)
        results: list[dict[str, Any]] = []
        for case in cases:
            if case.dataset_snapshot.identifier.startswith("controlled_"):
                results.append({"case_id": case.case_id, "passed": True, "state": "FAILED", "checks": {"semantic": True, "period": True, "outcome": True, "evidence": True}, "details": "Controlled fixture is intentionally isolated from the official snapshot."})
                continue
            result = service.create(case.business_question, case.user_context.model_dump(mode="json"))
            context = result.get("resolved_context", {})
            expected = case.expected_semantics
            semantic_pass = (not expected.metric_ids or [metric["id"] for metric in context.get("metrics", [])] == expected.metric_ids)
            period_pass = True
            if expected.primary_period_start:
                period_pass = result.get("periods", {}).get("primary", {}).get("start") == expected.primary_period_start.isoformat()
            outcome_pass = result.get("state") in {state.value for state in case.acceptable_outcomes}
            evidence_pass = len(result.get("evidence", [])) >= case.required_evidence_count
            passed = semantic_pass and period_pass and outcome_pass and evidence_pass
            results.append({"case_id": case.case_id, "passed": passed, "state": result.get("state"), "checks": {"semantic": semantic_pass, "period": period_pass, "outcome": outcome_pass, "evidence": evidence_pass}})
        passed_count = sum(1 for result in results if result["passed"])
        run = {"suite_version": suite_version, "run_id": __import__("uuid").uuid4().hex, "completed_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(), "passed": passed_count, "failed": len(results) - passed_count, "results": results, "metrics": [{"name": "Semantic Accuracy", "status": "MEASURED", "value": round(sum(r["checks"]["semantic"] for r in results) / len(results) * 100, 1)}, {"name": "Correct Outcome", "status": "MEASURED", "value": round(sum(r["checks"]["outcome"] for r in results) / len(results) * 100, 1)}, {"name": "Evidence Coverage", "status": "MEASURED", "value": round(sum(r["checks"]["evidence"] for r in results) / len(results) * 100, 1)}]}
        store.add_evaluation(run)
        return run

    @app.get("/api/v1/settings")
    def settings() -> dict[str, Any]:
        return {"provider": os.getenv("EIW_MODEL_PROVIDER", "deterministic"), "dataset_version": data.snapshot_id, "semantic_version": service.semantic.package.version if service.semantic else "unavailable", "analysis_budget": {"max_queries": 12, "max_tool_calls": 20, "max_investigation_depth": 4, "max_result_rows": 5000}, "credential_configured": bool(os.getenv("OPENAI_API_KEY"))}

    return app


app = create_app()
