"""Optional open-ended code-analysis lane backed by DeepAnalyze."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Any

from eiw.retail.data import RetailDataEngine
from eiw.retail.upstream import DeepAnalyzeWorker


class RetailCodeAnalyst:
    """Send a bounded analytical snapshot to an external code-analysis worker."""

    def __init__(self, data: RetailDataEngine, worker: DeepAnalyzeWorker) -> None:
        self.data = data
        self.worker = worker

    def analyze(
        self,
        instruction: str,
        *,
        current_weeks: list[int],
        previous_weeks: list[int],
        max_rows: int = 100,
    ) -> dict[str, Any]:
        rows = self.data.cross_dimension_scan(
            current_weeks,
            previous_weeks,
            limit=max_rows,
        )
        if not rows:
            return {
                "status": "NO_DATA",
                "instruction": instruction,
                "content": "",
                "rows_sent": 0,
            }

        with tempfile.TemporaryDirectory(prefix="retail-code-analyst-") as tmp:
            snapshot = Path(tmp) / "retail_driver_snapshot.csv"
            with snapshot.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            file_id = self.worker.upload_file(snapshot)
            prompt = (
                "You are a retail business analyst. Analyze only the attached bounded "
                "store-by-commodity driver snapshot. Distinguish observations from causal "
                "claims, quantify the strongest findings, and end with concrete next analyses "
                "or actions. User request: "
                + instruction
            )
            content = self.worker.analyze(prompt, file_ids=[file_id])

        return {
            "status": "COMPLETED",
            "instruction": instruction,
            "content": content,
            "rows_sent": len(rows),
            "provider": "DeepAnalyze",
        }
