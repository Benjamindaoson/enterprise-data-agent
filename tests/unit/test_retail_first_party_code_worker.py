from __future__ import annotations

from pathlib import Path
from typing import Any

from eiw.retail.code_worker import (
    FirstPartyRetailCodeAnalyst,
    GeneratedAnalysisCode,
    OpenAICompatibleCodeGenerator,
)
from eiw.retail.data import RetailDataEngine


class FakeGenerator:
    def generate(
        self,
        *,
        instruction: str,
        columns: list[str],
        sample_rows: list[dict[str, Any]],
    ) -> GeneratedAnalysisCode:
        assert instruction
        assert "sales_delta" in columns
        assert sample_rows
        return GeneratedAnalysisCode(
            code="result={'largest_abs_delta': 123.0}",
            explanation="fixture",
        )


class FakeSandbox:
    memory_mb = 256
    cpus = 0.5
    pids_limit = 16

    def execute(self, code: str, *, input_csv: Path) -> dict[str, Any]:
        assert "largest_abs_delta" in code
        assert input_csv.exists()
        return {
            "result": {"largest_abs_delta": 123.0},
            "stdout": "",
        }


def test_first_party_code_analyst_contract() -> None:
    data = RetailDataEngine.demo()
    analyst = FirstPartyRetailCodeAnalyst(
        data,
        FakeGenerator(),
        FakeSandbox(),
    )
    result = analyst.analyze(
        "Find the largest store-category movement.",
        current_weeks=[7, 8],
        previous_weeks=[5, 6],
        max_rows=20,
    )

    assert result["status"] == "COMPLETED"
    assert result["provider"] == "first-party-code-worker"
    assert result["rows_sent"] > 0
    assert result["result"]["largest_abs_delta"] == 123.0
    assert result["sandbox"]["network"] == "none"


def test_code_generator_json_parser_rejects_non_object() -> None:
    try:
        OpenAICompatibleCodeGenerator._parse_json("[1,2,3]")
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_code_generator_json_parser_accepts_wrapped_object() -> None:
    value = OpenAICompatibleCodeGenerator._parse_json(
        'prefix {"code":"result=1","explanation":"ok"} suffix'
    )
    assert value["code"] == "result=1"
