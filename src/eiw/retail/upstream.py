"""Optional external compatibility adapters.

The BA Agent product runtime is first-party. This module keeps only a bounded
compatibility adapter for users who already operate a DeepAnalyze service.
No upstream repository source is vendored or imported at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


class DeepAnalyzeWorker:
    """Compatibility adapter for an externally operated DeepAnalyze API."""

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
        service_root = (
            self.base_url[:-3]
            if self.base_url.endswith("/v1")
            else self.base_url
        )
        try:
            response = httpx.get(f"{service_root}/health", timeout=5.0)
            return response.is_success
        except httpx.HTTPError:
            return False

    def upload_file(self, path: Path) -> str:
        with (
            path.open("rb") as handle,
            httpx.Client(timeout=self.timeout_seconds) as client,
        ):
            response = client.post(
                f"{self.base_url}/files",
                headers={"Authorization": "Bearer dummy"},
                files={"file": (path.name, handle, "application/octet-stream")},
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload["id"])

    def analyze(
        self,
        instruction: str,
        *,
        file_ids: list[str] | None = None,
    ) -> str:
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
