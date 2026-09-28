"""Stable wrappers around temporarily reused upstream open-source components.

No first-party runtime imports upstream internals directly. These adapters make
replacement explicit and testable.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class UpstreamComponentStatus:
    name: str
    available: bool
    detail: str


class DeepAnalyzeWorker:
    """Adapter for the full DeepAnalyze API server (model + code execution)."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8200/v1",
        model: str = "DeepAnalyze-8B",
        timeout_seconds: float = 300.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def health(self) -> bool:
        service_root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        try:
            response = httpx.get(f"{service_root}/health", timeout=5.0)
            return response.is_success
        except httpx.HTTPError:
            return False

    def upload_file(self, path: Path) -> str:
        with path.open("rb") as handle, httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/files",
                headers={"Authorization": "Bearer dummy"},
                files={"file": (path.name, handle, "application/octet-stream")},
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload["id"])

    def analyze(self, instruction: str, *, file_ids: list[str] | None = None) -> str:
        message: dict[str, Any] = {"role": "user", "content": instruction}
        if file_ids:
            message["file_ids"] = file_ids
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "model": self.model,
                    "messages": [message],
                    "temperature": 0.2,
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload["choices"][0]["message"]["content"])


class WrenCliAdapter:
    """Optional Wren CLI bridge used during the bootstrap phase."""

    def __init__(self, *, executable: str = "wren", project_dir: Path | None = None) -> None:
        self.executable = executable
        self.project_dir = project_dir

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def ask(self, question: str) -> str:
        if not self.available():
            raise RuntimeError("Wren CLI is not installed on PATH")
        result = subprocess.run(
            [self.executable, "ask", question, "--direct"],
            cwd=self.project_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.stdout.strip()


class DataFormulatorBridge:
    """Describes the checked-out Data Formulator surface used by the bootstrap."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root

    def status(self) -> UpstreamComponentStatus:
        data_thread = self.repository_root / "src/views/DataThread.tsx"
        restyle = self.repository_root / "py-src/data_formulator/agents/agent_chart_restyle.py"
        ok = data_thread.exists() and restyle.exists()
        return UpstreamComponentStatus(
            name="data-formulator",
            available=ok,
            detail="Data Thread and chart-restyle modules present" if ok else "expected modules missing",
        )

    def manifest(self) -> dict[str, Any]:
        status = self.status()
        return {
            "name": status.name,
            "available": status.available,
            "detail": status.detail,
            "repository_root": str(self.repository_root),
            "integration_mode": "upstream-bootstrap",
        }


def upstream_manifest(root: Path) -> dict[str, Any]:
    components = {
        "deepanalyze": root / "third_party/deepanalyze",
        "data_formulator": root / "third_party/data-formulator",
        "wrenai": root / "third_party/wrenai",
    }
    return {
        name: {
            "path": str(path),
            "available": path.exists(),
        }
        for name, path in components.items()
    }
