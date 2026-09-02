"""Immutable snapshot resolution and data-coverage guards."""

from datetime import date

from eiw.domain.models import DatasetManifest, VersionRef


class SnapshotResolutionError(ValueError):
    """Raised when a task attempts to execute against a mutable or unknown source."""


class MetricCoverageError(ValueError):
    """Raised when a metric is requested outside its declared usable coverage."""


class SnapshotRegistry:
    """Maps a logical rolling alias to a versioned, content-addressed snapshot.

    The mapping is resolved during context compilation, then the returned version
    reference is persisted into task, evidence, artifacts, and evaluation runs.
    """

    def __init__(self, manifests: dict[str, DatasetManifest], aliases: dict[str, str]) -> None:
        self._manifests = manifests
        self._aliases = aliases

    def resolve(self, identifier: str) -> VersionRef:
        snapshot_id = self._aliases.get(identifier, identifier)
        manifest = self._manifests.get(snapshot_id)
        if manifest is None:
            raise SnapshotResolutionError(f"unknown or unresolved dataset identifier: {identifier}")
        if manifest.status != "READY":
            raise SnapshotResolutionError(f"dataset snapshot is not READY: {snapshot_id}")
        return VersionRef(
            identifier=manifest.snapshot_id,
            version=manifest.extracted_at.date().isoformat(),
            content_hash=manifest.curated_file_sha256 or manifest.raw_file_sha256,
        )

    @staticmethod
    def require_coverage(
        metric_id: str,
        start_date: date,
        end_date: date,
        available_from: date,
        available_to: date,
    ) -> None:
        if start_date < available_from or end_date > available_to:
            raise MetricCoverageError(
                f"{metric_id} is unavailable for {start_date.isoformat()} to {end_date.isoformat()}; "
                f"coverage is {available_from.isoformat()} to {available_to.isoformat()}"
            )
