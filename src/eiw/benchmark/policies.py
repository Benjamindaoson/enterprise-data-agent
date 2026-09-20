"""Reference policies for BusinessAgentBench."""

from __future__ import annotations

import random

from eiw.benchmark.hard_env import HARD_ACTION_SPACE, HardState


class HardExpertPolicy:
    def choose_action(self, state: HardState) -> str:
        valid = self._valid(state)
        priority = (
            "retry_tool",
            "replan",
            "retrieve_memory",
            "inspect_metric",
            "cross_check",
            "inspect_segment",
            "build_proposal",
            "request_approval",
            "execute_action",
            "stop",
        )
        for action in priority:
            if action in valid:
                return action
        return "replan"

    @staticmethod
    def _valid(state: HardState) -> set[str]:
        # Mirror the public, observable decision rules; no hidden-driver access.
        if state.tool_failed and not state.recovered:
            return {"retry_tool", "replan"}
        valid: set[str] = set()
        if not state.metric_seen:
            valid.add("inspect_metric")
        if state.metric_seen and not state.segment_seen:
            valid.add("inspect_segment")
        if state.case.requires_memory and not state.memory_loaded:
            valid.add("retrieve_memory")
        if (
            state.case.evidence_mode.value != "CLEAN"
            and state.metric_seen
            and not state.cross_checked
        ) or (state.case.alternate_path and state.metric_seen and not state.cross_checked):
            valid.add("cross_check")
        evidence_ready = state.metric_seen and (
            state.segment_seen or (state.case.alternate_path and state.cross_checked)
        )
        memory_ready = not state.case.requires_memory or state.memory_loaded
        conflict_ready = state.case.evidence_mode.value == "CLEAN" or state.cross_checked
        recovery_ready = not state.tool_failed or state.recovered
        if evidence_ready and memory_ready and conflict_ready and recovery_ready and not state.proposal_ready:
            valid.add("build_proposal")
        if state.proposal_ready and state.case.scenario.value != "ANALYTICS":
            if not state.approval_granted:
                valid.add("request_approval")
            else:
                valid.update({"execute_action", "stop"})
        if state.proposal_ready and state.case.scenario.value == "ANALYTICS":
            valid.add("stop")
        return valid or {"replan"}


class PromptHeuristicPolicy:
    """Intentionally imperfect prompt-like policy.

    It handles ordinary evidence collection and approval, but does not reliably
    use memory, cross-check conflicts or recover from every tool failure.
    """

    def choose_action(self, state: HardState) -> str:
        if state.tool_failed:
            return "retry_tool" if state.step % 2 == 0 else "replan"
        if not state.metric_seen:
            return "inspect_metric"
        if not state.segment_seen:
            return "inspect_segment"
        if state.case.requires_memory and not state.memory_loaded and state.step % 3 != 0:
            return "retrieve_memory"
        if (
            state.case.evidence_mode.value == "CONFLICTING"
            and not state.cross_checked
            and state.step % 2 == 0
        ):
            return "cross_check"
        if not state.proposal_ready:
            return "build_proposal"
        if state.case.scenario.value == "ANALYTICS":
            return "stop"
        if not state.approval_granted:
            return "request_approval"
        return "execute_action"


class DirectPolicy:
    def choose_action(self, state: HardState) -> str:
        if state.case.scenario.value == "ANALYTICS":
            return "build_proposal" if not state.proposal_ready else "stop"
        return "execute_action"


class HardRandomPolicy:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def choose_action(self, state: HardState) -> str:
        return self.rng.choice(HARD_ACTION_SPACE)
