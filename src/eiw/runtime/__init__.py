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
    "SkillDefinition",
    "SkillRegistry",
    "default_skill_registry",
]

_EXPORTS = {
    "ActionPolicy": ("eiw.runtime.governance", "ActionPolicy"),
    "RuntimeBudget": ("eiw.runtime.governance", "RuntimeBudget"),
    "MemoryKind": ("eiw.runtime.memory", "MemoryKind"),
    "MemoryRecord": ("eiw.runtime.memory", "MemoryRecord"),
    "MemoryStore": ("eiw.runtime.memory", "MemoryStore"),
    "SkillDefinition": ("eiw.runtime.skills", "SkillDefinition"),
    "SkillRegistry": ("eiw.runtime.skills", "SkillRegistry"),
    "default_skill_registry": ("eiw.runtime.skills", "default_skill_registry"),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    return getattr(import_module(module_name), attribute)


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
