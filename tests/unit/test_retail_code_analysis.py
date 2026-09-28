from pathlib import Path

from eiw.retail.code_analysis import RetailCodeAnalyst
from eiw.retail.data import RetailDataEngine


class FakeDeepAnalyzeWorker:
    def __init__(self) -> None:
        self.uploaded_rows = 0

    def upload_file(self, path: Path) -> str:
        self.uploaded_rows = max(0, len(path.read_text(encoding="utf-8").splitlines()) - 1)
        return "file-demo"

    def analyze(self, instruction: str, *, file_ids: list[str] | None = None) -> str:
        assert file_ids == ["file-demo"]
        assert "causal claims" in instruction
        return "The largest decline is concentrated in a small store × commodity slice."


def test_code_analyst_sends_bounded_snapshot_to_worker() -> None:
    worker = FakeDeepAnalyzeWorker()
    analyst = RetailCodeAnalyst(RetailDataEngine.demo(), worker)  # type: ignore[arg-type]

    result = analyst.analyze(
        "Find patterns the deterministic skills may have missed.",
        current_weeks=[7, 8],
        previous_weeks=[5, 6],
        max_rows=20,
    )

    assert result["status"] == "COMPLETED"
    assert result["provider"] == "DeepAnalyze"
    assert 0 < result["rows_sent"] <= 20
    assert worker.uploaded_rows == result["rows_sent"]
