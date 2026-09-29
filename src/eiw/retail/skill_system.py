"""Retail Skill catalog backed by the generic versioned Skill runtime."""

from __future__ import annotations

from eiw.retail.models import WorkstreamName
from eiw.runtime.skills import SkillCollection, SkillDefinition, SkillRegistry


def _skill(
    skill_id: str,
    description: str,
    *,
    workstream: WorkstreamName,
    tags: tuple[str, ...],
    intents: tuple[str, ...],
    tool: str,
) -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        description=description,
        input_schema={"current_weeks": "list[int]", "previous_weeks": "list[int]"},
        output_schema={"result": "structured"},
        tool_dependencies=(tool,),
        permissions=("analytics:read",),
        tags=("retail", "analytics", *tags),
        workstreams=(workstream.value,),
        intents=intents,
        implementation_ref=f"retail.{skill_id}",
    )


def retail_skill_registry() -> SkillRegistry:
    """Return the 12 promoted Retail BA Skills used by specialist agents."""

    registry = SkillRegistry()
    definitions = (
        _skill(
            "kpi_overview",
            "Compare governed business KPIs across analysis periods.",
            workstream=WorkstreamName.OVERVIEW,
            tags=("kpi", "overview", "trend"),
            intents=("overview", "compare", "trend"),
            tool="retail.overview",
        ),
        _skill(
            "store_contribution",
            "Rank store contributions to observed business movement.",
            workstream=WorkstreamName.STORE,
            tags=("store", "contribution", "driver"),
            intents=("store", "driver", "attribution"),
            tool="retail.contribution.store",
        ),
        _skill(
            "store_anomaly",
            "Detect unusual store-level performance patterns.",
            workstream=WorkstreamName.STORE,
            tags=("store", "anomaly"),
            intents=("store", "anomaly", "outlier"),
            tool="retail.store_anomaly",
        ),
        _skill(
            "store_commodity_scan",
            "Scan store-by-commodity combinations for concentrated drivers.",
            workstream=WorkstreamName.STORE,
            tags=("store", "commodity", "cross-dimension"),
            intents=("store", "commodity", "drilldown"),
            tool="retail.store_commodity_scan",
        ),
        _skill(
            "commodity_contribution",
            "Rank commodity contributions to observed business movement.",
            workstream=WorkstreamName.PRODUCT,
            tags=("product", "commodity", "contribution"),
            intents=("product", "driver", "attribution"),
            tool="retail.contribution.commodity",
        ),
        _skill(
            "price_volume",
            "Decompose product movement into price and volume effects.",
            workstream=WorkstreamName.PRODUCT,
            tags=("product", "price", "volume"),
            intents=("price", "volume", "decomposition"),
            tool="retail.price_volume",
        ),
        _skill(
            "merchandising",
            "Compare observed performance across merchandising and display states.",
            workstream=WorkstreamName.PROMOTION,
            tags=("promotion", "merchandising", "display"),
            intents=("promotion", "merchandising"),
            tool="retail.promotion_performance",
        ),
        _skill(
            "customer_segments",
            "Rank customer concentration and segment contribution.",
            workstream=WorkstreamName.CUSTOMER,
            tags=("customer", "segment"),
            intents=("customer", "segment", "concentration"),
            tool="retail.customer_segments",
        ),
        _skill(
            "basket_affinity",
            "Measure frequently co-occurring product pairs in observed baskets.",
            workstream=WorkstreamName.CUSTOMER,
            tags=("customer", "basket", "affinity"),
            intents=("basket", "affinity", "cross-sell"),
            tool="retail.basket_affinity",
        ),
        _skill(
            "income_segments",
            "Compare observed business movement across income segments.",
            workstream=WorkstreamName.CUSTOMER,
            tags=("customer", "income", "demographic"),
            intents=("income", "demographic", "segment"),
            tool="retail.demographic.income",
        ),
        _skill(
            "household_composition",
            "Compare observed business movement across household composition segments.",
            workstream=WorkstreamName.CUSTOMER,
            tags=("customer", "household", "demographic"),
            intents=("household", "demographic", "segment"),
            tool="retail.demographic.household",
        ),
        _skill(
            "coupon_funnel",
            "Describe campaign targeting and coupon redemption funnel observations.",
            workstream=WorkstreamName.CUSTOMER,
            tags=("customer", "coupon", "campaign", "funnel"),
            intents=("coupon", "campaign", "funnel"),
            tool="retail.coupon_funnel",
        ),
    )
    for definition in definitions:
        registry.register(definition)

    for workstream in WorkstreamName:
        skill_ids = tuple(
            skill.skill_id
            for skill in registry.list()
            if workstream.value in skill.workstreams
        )
        registry.register_collection(
            SkillCollection(
                collection_id=f"retail.{workstream.value}",
                description=f"Promoted Skills for the {workstream.value} specialist.",
                skill_ids=skill_ids,
                tags=("retail", workstream.value),
            )
        )
    return registry
