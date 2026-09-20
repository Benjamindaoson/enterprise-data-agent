"""Golden-case loader with strict contract validation."""

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from eiw.domain.models import EvaluationCase


def load_cases(path: Path) -> tuple[str, list[EvaluationCase]]:
    parsed = yaml.safe_load(path.read_bytes())
    if not isinstance(parsed, dict) or "suite_version" not in parsed or "cases" not in parsed:
        raise ValueError("evaluation suite requires suite_version and cases")
    cases = [EvaluationCase.model_validate(raw_case) for raw_case in parsed["cases"]]
    identifiers = [case.case_id for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("evaluation case IDs must be unique")
    return str(parsed["suite_version"]), cases
