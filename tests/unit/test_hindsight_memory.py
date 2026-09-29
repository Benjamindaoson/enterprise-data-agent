from __future__ import annotations

from types import SimpleNamespace

from eiw.runtime.long_term_memory import HindsightLongTermMemory


class FakeHindsightClient:
    def __init__(self) -> None:
        self.retains: list[dict[str, object]] = []
        self.recalls: list[dict[str, object]] = []
        self.reflections: list[dict[str, object]] = []

    def recall(self, **kwargs):
        self.recalls.append(kwargs)
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    id="m1",
                    text="Store investigations should start with contribution.",
                    type="observation",
                    context="prior successful analysis",
                    tags=["analysis"],
                    metadata={"source": "task-1"},
                )
            ]
        )

    def retain(self, **kwargs):
        self.retains.append(kwargs)
        return SimpleNamespace(items_count=1)

    def reflect(self, **kwargs):
        self.reflections.append(kwargs)
        return SimpleNamespace(text="Prefer contribution before anomaly scans.")


def test_hindsight_adapter_recall_retain_reflect() -> None:
    client = FakeHindsightClient()
    memory = HindsightLongTermMemory(
        base_url="http://memory.test",
        bank_prefix="test",
        client=client,
    )

    items = memory.recall("domain:retail", "Why did sales change?")
    assert items[0].memory_type == "observation"
    assert "contribution" in items[0].text
    assert client.recalls[0]["prefer_observations"] is True

    memory.retain(
        "domain:retail",
        "Completed store investigation.",
        context="completed analysis",
        tags=("analysis",),
    )
    assert client.retains[0]["bank_id"] == memory.bank_id("domain:retail")

    reflected = memory.reflect("domain:retail", "What strategy should be reused?")
    assert "contribution" in reflected
