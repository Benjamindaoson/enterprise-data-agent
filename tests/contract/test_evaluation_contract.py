from pathlib import Path

from eiw.domain.enums import TaskState
from eiw.evaluation.loader import load_cases


def test_initial_golden_suite_is_loadable_and_unique() -> None:
    suite_version, cases = load_cases(Path("evaluation/cases/phase0-initial.yaml"))
    assert suite_version == "0.1.0"
    assert len(cases) == 12
    assert len({case.case_id for case in cases}) == len(cases)


def test_golden_suite_exercises_critical_boundaries() -> None:
    _, cases = load_cases(Path("evaluation/cases/phase0-initial.yaml"))
    by_id = {case.case_id: case for case in cases}
    assert by_id["GC-006"].expected_semantics.must_request_clarification
    assert TaskState.PARTIAL in by_id["GC-011"].acceptable_outcomes
    assert "join" in by_id["GC-009"].tags
