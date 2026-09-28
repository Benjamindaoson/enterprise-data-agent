"""Versioned immutable ontology storage with explicit promotion."""

from __future__ import annotations

import json
from pathlib import Path

from eiw.ontology.models import OntologyState


class OntologyStore:
    """Keep candidate versions immutable and promotion as a separate pointer."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._states: dict[str, dict[str, OntologyState]] = {}
        self._current: dict[str, str] = {}
        if self.path is not None and self.path.exists():
            self._load()

    def put(self, state: OntologyState, *, make_current: bool = False) -> None:
        versions = self._states.setdefault(state.ontology_id, {})
        existing = versions.get(state.version)
        if existing is not None and existing.content_hash != state.content_hash:
            raise ValueError(
                f"ontology version is immutable: "
                f"{state.ontology_id}@{state.version}"
            )
        versions[state.version] = state
        if make_current:
            self.promote(state.ontology_id, state.version)
        else:
            self._persist()

    def has(self, ontology_id: str, version: str | None = None) -> bool:
        if version is None:
            return ontology_id in self._current
        return version in self._states.get(ontology_id, {})

    def get(self, ontology_id: str, version: str) -> OntologyState:
        try:
            return self._states[ontology_id][version]
        except KeyError as exc:
            raise KeyError(f"unknown ontology version: {ontology_id}@{version}") from exc

    def current(self, ontology_id: str) -> OntologyState:
        try:
            version = self._current[ontology_id]
        except KeyError as exc:
            raise KeyError(f"no promoted ontology: {ontology_id}") from exc
        return self.get(ontology_id, version)

    def versions(self, ontology_id: str) -> list[str]:
        return sorted(self._states.get(ontology_id, {}))

    def ontology_ids(self) -> list[str]:
        return sorted(self._states)

    def promote(
        self,
        ontology_id: str,
        version: str,
        *,
        expected_parent_version: str | None = None,
    ) -> OntologyState:
        candidate = self.get(ontology_id, version)
        current_version = self._current.get(ontology_id)
        if expected_parent_version is not None and current_version != expected_parent_version:
            raise ValueError(
                f"promotion parent changed: expected {expected_parent_version}, "
                f"current {current_version}"
            )
        if (
            current_version is not None
            and candidate.parent_version is not None
            and candidate.parent_version != current_version
        ):
            raise ValueError(
                f"candidate parent {candidate.parent_version} does not match "
                f"current version {current_version}"
            )
        self._current[ontology_id] = version
        self._persist()
        return candidate

    def _persist(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "current": self._current,
            "states": [
                state.model_dump(mode="json")
                for ontology_id in sorted(self._states)
                for _, state in sorted(self._states[ontology_id].items())
            ],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def _load(self) -> None:
        assert self.path is not None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        for raw in payload.get("states", []):
            state = OntologyState.model_validate(raw)
            self._states.setdefault(state.ontology_id, {})[state.version] = state
        self._current = {
            str(key): str(value)
            for key, value in dict(payload.get("current", {})).items()
        }
