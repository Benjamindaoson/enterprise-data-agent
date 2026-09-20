import io
import zipfile
from pathlib import Path

from eiw.benchmark.public_data import (
    dataset_manifest,
    profile_bank_marketing,
    write_business_agent_benchmark,
)


def _bank_zip(path: Path) -> Path:
    csv_text = (
        '"age";"job";"contact";"campaign";"y"\n'
        '30;"admin.";"cellular";1;"yes"\n'
        '45;"services";"telephone";2;"no"\n'
        '39;"admin.";"cellular";1;"yes"\n'
        '50;"services";"cellular";3;"no"\n'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("bank/bank-full.csv", csv_text)
    path.write_bytes(buffer.getvalue())
    return path


def test_public_dataset_registry_has_business_licenses_and_scenarios():
    manifest = dataset_manifest()
    assert {item["dataset_id"] for item in manifest} == {
        "uci-bank-marketing",
        "uci-online-retail",
    }
    assert all(item["license"] == "CC BY 4.0" for item in manifest)


def test_bank_profile_and_real_benchmark_generation(tmp_path: Path):
    profile = profile_bank_marketing(_bank_zip(tmp_path / "bank.zip"))
    assert profile["row_count"] == 4
    assert profile["conversion_rate"] == 0.5
    assert profile["conversion_by_contact"]["cellular"] > profile["conversion_by_contact"]["telephone"]

    payload = write_business_agent_benchmark(
        tmp_path / "bench.json",
        bank_profile=profile,
    )
    assert len(payload["tasks"]) == 3
    assert {task["category"] for task in payload["tasks"]} == {
        "Marketing Budget",
        "Sales Expansion",
        "Tool Use",
    }
