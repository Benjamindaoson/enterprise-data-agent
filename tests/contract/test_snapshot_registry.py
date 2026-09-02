from datetime import UTC, date, datetime

import pytest

from eiw.data.snapshot import MetricCoverageError, SnapshotRegistry
from eiw.domain.models import DatasetManifest


def ready_manifest() -> DatasetManifest:
    return DatasetManifest(
        snapshot_id="iowa_liquor_snapshot_2026_07_v1",
        source_url="https://data.iowa.gov/catalog/dataset/1051",
        extracted_at=datetime(2026, 9, 1, tzinfo=UTC),
        business_date_min=date(2024, 1, 1),
        business_date_max=date(2026, 7, 31),
        raw_file_sha256="a" * 64,
        curated_file_sha256="b" * 64,
        row_count=1,
        schema_hash="c" * 64,
        license="CC BY 4.0",
        status="READY",
    )


def test_rolling_alias_resolves_before_execution() -> None:
    manifest = ready_manifest()
    registry = SnapshotRegistry(
        manifests={manifest.snapshot_id: manifest},
        aliases={"iowa_liquor_rolling": manifest.snapshot_id},
    )
    resolved = registry.resolve("iowa_liquor_rolling")
    assert resolved.identifier == manifest.snapshot_id
    assert resolved.content_hash == "b" * 64


def test_cost_coverage_cannot_be_silently_zero_filled() -> None:
    with pytest.raises(MetricCoverageError, match="wholesale_gross_spread is unavailable"):
        SnapshotRegistry.require_coverage(
            "wholesale_gross_spread",
            date(2024, 3, 1),
            date(2024, 3, 31),
            date(2025, 7, 1),
            date(2026, 7, 31),
        )
