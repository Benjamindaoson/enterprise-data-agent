"""Business intelligence and autonomous-operations contracts.

Package initialization stays lazy so importing business models does not
recursively import runtime governance through the operations service.
"""

from __future__ import annotations

from importlib import import_module

__all__ = ["BusinessOperationsService"]


def __getattr__(name: str) -> object:
    if name != "BusinessOperationsService":
        raise AttributeError(name)
    return getattr(import_module("eiw.business.operations"), name)


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
