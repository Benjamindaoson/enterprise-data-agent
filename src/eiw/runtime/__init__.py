"""Reusable runtime capabilities for long-horizon enterprise agents.

Imports are resolved lazily to keep package initialization acyclic. Runtime
submodules must be importable without eagerly loading business governance.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "ActionPolicy",
    "RuntimeBudget",
    "MemoryKind",
    "MemoryRecord",
    "MemoryStore",
    "SkillCollection",
    "SkillDefinition",
    "SkillLifecycle",
    "SkillRegistry",
    "SkillRisk",
    "SkillSchedule",
    "SkillScheduleRequest",
    "SkillScheduler",
    "ScheduledSkill",
    "default_skill_registry",
    "PairedSkillEvolutionGate",
    "SkillCandidateFactory",
    "SkillEvolutionEngine",
    "SkillEvolutionMetrics",
    "SkillGapMiner",
    "SkillGapSignature",
    "SkillTrajectoryFailure",
]

_EXPORTS = {
    "ActionPolicy": ("eiw.runtime.governance", "ActionPolicy"),
    "RuntimeBudget": ("eiw.runtime.governance", "RuntimeBudget"),
    "MemoryKind": ("eiw.runtime.memory", "MemoryKind"),
    "MemoryRecord": ("eiw.runtime.memory", "MemoryRecord"),
    "MemoryStore": ("eiw.runtime.memory", "MemoryStore"),
    "SkillCollection": ("eiw.runtime.skills", "SkillCollection"),
    "SkillDefinition": ("eiw.runtime.skills", "SkillDefinition"),
    "SkillLifecycle": ("eiw.runtime.skills", "SkillLifecycle"),
    "SkillRegistry": ("eiw.runtime.skills", "SkillRegistry"),
    "SkillRisk": ("eiw.runtime.skills", "SkillRisk"),
    "SkillSchedule": ("eiw.runtime.skills", "SkillSchedule"),
    "SkillScheduleRequest": ("eiw.runtime.skills", "SkillScheduleRequest"),
    "SkillScheduler": ("eiw.runtime.skills", "SkillScheduler"),
    "ScheduledSkill": ("eiw.runtime.skills", "ScheduledSkill"),
    "default_skill_registry": ("eiw.runtime.skills", "default_skill_registry"),
    "PairedSkillEvolutionGate": (
        "eiw.runtime.skill_evolution",
        "PairedSkillEvolutionGate",
    ),
    "SkillCandidateFactory": ("eiw.runtime.skill_evolution", "SkillCandidateFactory"),
    "SkillEvolutionEngine": ("eiw.runtime.skill_evolution", "SkillEvolutionEngine"),
    "SkillEvolutionMetrics": ("eiw.runtime.skill_evolution", "SkillEvolutionMetrics"),
    "SkillGapMiner": ("eiw.runtime.skill_evolution", "SkillGapMiner"),
    "SkillGapSignature": ("eiw.runtime.skill_evolution", "SkillGapSignature"),
    "SkillTrajectoryFailure": (
        "eiw.runtime.skill_evolution",
        "SkillTrajectoryFailure",
    ),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    return getattr(import_module(module_name), attribute)


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
