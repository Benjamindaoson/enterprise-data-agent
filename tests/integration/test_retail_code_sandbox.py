from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest

from eiw.retail.code_worker import DockerCodeSandbox


@pytest.mark.integration
def test_docker_code_sandbox_executes_polars_without_network(tmp_path: Path) -> None:
    if shutil.which("docker") is None:
        pytest.skip("Docker is required")

    input_path = tmp_path / "input.csv"
    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["segment", "delta"])
        writer.writeheader()
        writer.writerows(
            [
                {"segment": "A", "delta": -10.0},
                {"segment": "B", "delta": 25.0},
            ]
        )

    sandbox = DockerCodeSandbox(timeout_seconds=120.0)
    result = sandbox.execute(
        (
            "import polars as pl\n"
            "df=pl.read_csv(data_path)\n"
            "row=df.sort(pl.col('delta').abs(), descending=True).row(0, named=True)\n"
            "result={'segment':row['segment'],'delta':float(row['delta']),"
            "'rows':df.height}"
        ),
        input_csv=input_path,
    )

    assert result["result"] == {"segment": "B", "delta": 25.0, "rows": 2}
