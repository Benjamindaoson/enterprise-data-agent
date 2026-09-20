"""Baseline and expert policies for flywheel data generation."""

from __future__ import annotations

import random

from eiw.business.simulator import ACTION_SPACE, EXPECTED_PATHS, SimulatorState


class ExpertPolicy:
    def choose_action(self, state: SimulatorState) -> str:
        path = EXPECTED_PATHS[state.scenario]
        return path[min(state.step_index, len(path) - 1)]


class RandomPolicy:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def choose_action(self, state: SimulatorState) -> str:
        return self.rng.choice(ACTION_SPACE)
