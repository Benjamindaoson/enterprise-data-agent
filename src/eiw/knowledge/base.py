"""Knowledge Base for Enterprise Data Agent.

Provides structured knowledge retrieval for:
- Business glossary
- Metric definitions
- Data dictionary
- Table/column documentation
- Lineage notes
- Business rules
- Approved SQL examples
- Analyst playbook / FAQ
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DomainModel(BaseModel):
    """Base model with strict validation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class KnowledgeSourceType(str, Enum):
    """Types of knowledge sources."""

    BUSINESS_GLOSSARY = "business_glossary"
    METRIC_DEFINITION = "metric_definition"
    DATA_DICTIONARY = "data_dictionary"
    TABLE_DOCUMENTATION = "table_documentation"
    COLUMN_DOCUMENTATION = "column_documentation"
    LINEAGE_NOTE = "lineage_note"
    BUSINESS_RULE = "business_rule"
    SQL_EXAMPLE = "sql_example"
    ANALYST_FAQ = "analyst_faq"
    POLICY_DOCUMENT = "policy_document"


class PermissionLevel(str, Enum):
    """Permission levels for knowledge access."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class KnowledgeItem(DomainModel):
    """A single knowledge item."""

    item_id: UUID = Field(default_factory=uuid4)
    source_type: KnowledgeSourceType

    # Content
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=10000)

    # References
    domain_id: str | None = None
    semantic_version: str | None = None

    # Tags for retrieval
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    # Related entities
    related_metric_ids: list[str] = Field(default_factory=list)
    related_dimension_ids: list[str] = Field(default_factory=list)
    related_table_names: list[str] = Field(default_factory=list)
    related_column_names: list[str] = Field(default_factory=list)

    # Access control (NOT the source of authorization)
    permission_level: PermissionLevel = PermissionLevel.INTERNAL

    # Metadata
    author: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0.0"

    # Content integrity
    content_hash: str = Field(default="")

    @field_validator("content_hash", mode="before")
    @classmethod
    def compute_hash(cls, v: str | None) -> str:
        return v or ""


class KnowledgeRetrievalQuery(DomainModel):
    """Query for knowledge retrieval."""

    query_text: str = Field(min_length=1, max_length=1000)
    query_type: KnowledgeSourceType | None = None

    # Filters
    domain_ids: list[str] = Field(default_factory=list)
    semantic_versions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    related_metric_ids: list[str] = Field(default_factory=list)

    # Permission filter (applied AFTER retrieval)
    max_permission_level: PermissionLevel = PermissionLevel.RESTRICTED

    # Retrieval options
    max_results: int = Field(default=10, ge=1, le=50)
    include_content: bool = True


class KnowledgeRetrievalResult(DomainModel):
    """Result of knowledge retrieval."""

    items: list[KnowledgeItem] = Field(default_factory=list)
    total_found: int = Field(default=0)
    query_text: str
    retrieval_time_ms: float | None = None

    # Source/version references
    domains_searched: list[str] = Field(default_factory=list)
    semantic_versions_used: list[str] = Field(default_factory=list)


class KnowledgeBase:
    """Knowledge base for retrieval.

    This is a simple in-memory knowledge base. In production, this would
    be backed by a vector database or search index.
    """

    def __init__(self) -> None:
        """Initialize knowledge base."""
        self._items: dict[UUID, KnowledgeItem] = {}
        self._index: dict[str, list[UUID]] = {}  # keyword -> item IDs

    def add_item(self, item: KnowledgeItem) -> None:
        """Add a knowledge item."""
        # Compute content hash if not set
        if not item.content_hash:
            item.content_hash = hashlib.sha256(
                item.content.encode()
            ).hexdigest()[:16]

        # Store item
        self._items[item.item_id] = item

        # Update index
        for keyword in item.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower not in self._index:
                self._index[keyword_lower] = []
            if item.item_id not in self._index[keyword_lower]:
                self._index[keyword_lower].append(item.item_id)

        # Also index by tags
        for tag in item.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._index:
                self._index[tag_lower] = []
            if item.item_id not in self._index[tag_lower]:
                self._index[tag_lower].append(item.item_id)

    def retrieve(
        self,
        query: KnowledgeRetrievalQuery,
    ) -> KnowledgeRetrievalResult:
        """Retrieve knowledge items matching query.

        This method implements permission-aware retrieval. Items are filtered
        based on permission level AFTER ranking, ensuring that:
        1. The most relevant items are found first
        2. Permission filtering only removes items, never promotes them
        3. RAG content CANNOT grant permissions - permissions come from Governance
        """
        import time

        start_time = time.time()

        # Find matching items
        query_keywords = set(query.query_text.lower().split())
        matching_ids: dict[UUID, int] = {}  # item_id -> relevance score

        for keyword in query_keywords:
            if keyword in self._index:
                for item_id in self._index[keyword]:
                    if item_id in matching_ids:
                        matching_ids[item_id] += 1
                    else:
                        matching_ids[item_id] = 1

        # Also check title and content matches
        query_lower = query.query_text.lower()
        for item_id, item in self._items.items():
            if query_lower in item.title.lower():
                matching_ids[item_id] = matching_ids.get(item_id, 0) + 5
            if query_lower in item.content.lower():
                matching_ids[item_id] = matching_ids.get(item_id, 0) + 2

        # Sort by relevance
        sorted_ids = sorted(
            matching_ids.keys(),
            key=lambda x: matching_ids[x],
            reverse=True,
        )

        # Apply filters and permission check
        results: list[KnowledgeItem] = []
        for item_id in sorted_ids:
            if len(results) >= query.max_results:
                break

            item = self._items[item_id]

            # Filter by query type
            if query.query_type and item.source_type != query.query_type:
                continue

            # Filter by domain
            if query.domain_ids and item.domain_id not in query.domain_ids:
                continue

            # Filter by semantic version
            if query.semantic_versions:
                if item.semantic_version not in query.semantic_versions:
                    continue

            # Filter by tags
            if query.tags:
                if not any(tag in item.tags for tag in query.tags):
                    continue

            # Filter by related metrics
            if query.related_metric_ids:
                if not any(
                    mid in item.related_metric_ids
                    for mid in query.related_metric_ids
                ):
                    continue

            # Apply permission filter (permissive - only filter above max)
            # NOTE: This is a safeguard, not authorization.
            # Real authorization comes from Governance layer.
            if not self._check_permission(
                item.permission_level,
                query.max_permission_level,
            ):
                continue

            results.append(item)

        retrieval_time_ms = (time.time() - start_time) * 1000

        return KnowledgeRetrievalResult(
            items=results,
            total_found=len(results),
            query_text=query.query_text,
            retrieval_time_ms=retrieval_time_ms,
            domains_searched=list(set(
                item.domain_id for item in results if item.domain_id
            )),
            semantic_versions_used=list(set(
                item.semantic_version for item in results if item.semantic_version
            )),
        )

    def _check_permission(
        self,
        item_permission: PermissionLevel,
        max_allowed: PermissionLevel,
    ) -> bool:
        """Check if item permission is within allowed level.

        Note: This is a retrieval filter, NOT an authorization decision.
        Authorization must come from Governance.
        """
        permission_order = {
            PermissionLevel.PUBLIC: 1,
            PermissionLevel.INTERNAL: 2,
            PermissionLevel.CONFIDENTIAL: 3,
            PermissionLevel.RESTRICTED: 4,
        }

        return permission_order.get(item_permission, 99) <= permission_order.get(
            max_allowed, 0
        )

    def get_by_id(self, item_id: UUID) -> KnowledgeItem | None:
        """Get a knowledge item by ID."""
        return self._items.get(item_id)

    def get_by_source_type(
        self,
        source_type: KnowledgeSourceType,
    ) -> list[KnowledgeItem]:
        """Get all items of a given source type."""
        return [
            item for item in self._items.values()
            if item.source_type == source_type
        ]

    def get_metric_definitions(
        self,
        metric_ids: list[str] | None = None,
    ) -> list[KnowledgeItem]:
        """Get metric definition knowledge items."""
        items = self.get_by_source_type(KnowledgeSourceType.METRIC_DEFINITION)
        if metric_ids:
            items = [
                item for item in items
                if any(mid in item.related_metric_ids for mid in metric_ids)
            ]
        return items

    def get_glossary_terms(
        self,
        domain_id: str | None = None,
    ) -> list[KnowledgeItem]:
        """Get business glossary terms."""
        items = self.get_by_source_type(KnowledgeSourceType.BUSINESS_GLOSSARY)
        if domain_id:
            items = [item for item in items if item.domain_id == domain_id]
        return items

    def get_sql_examples(
        self,
        related_metric_ids: list[str] | None = None,
    ) -> list[KnowledgeItem]:
        """Get SQL example knowledge items."""
        items = self.get_by_source_type(KnowledgeSourceType.SQL_EXAMPLE)
        if related_metric_ids:
            items = [
                item for item in items
                if any(mid in item.related_metric_ids for mid in related_metric_ids)
            ]
        return items

    def size(self) -> int:
        """Get number of items in knowledge base."""
        return len(self._items)


# =============================================================================
# Knowledge item factories
# =============================================================================


def create_metric_definition_item(
    metric_id: str,
    metric_name: str,
    description: str,
    formula: str,
    unit: str,
    domain_id: str,
    semantic_version: str,
    **kwargs: Any,
) -> KnowledgeItem:
    """Create a metric definition knowledge item."""
    return KnowledgeItem(
        source_type=KnowledgeSourceType.METRIC_DEFINITION,
        title=f"Metric: {metric_name} ({metric_id})",
        content=f"{description}\n\nFormula: {formula}\n\nUnit: {unit}",
        domain_id=domain_id,
        semantic_version=semantic_version,
        tags=["metric", "definition", metric_id],
        keywords=[metric_id, metric_name, unit, "metric"],
        related_metric_ids=[metric_id],
        **kwargs,
    )


def create_glossary_item(
    term: str,
    definition: str,
    domain_id: str | None = None,
    related_metric_ids: list[str] | None = None,
    **kwargs: Any,
) -> KnowledgeItem:
    """Create a glossary term knowledge item."""
    return KnowledgeItem(
        source_type=KnowledgeSourceType.BUSINESS_GLOSSARY,
        title=f"Glossary: {term}",
        content=definition,
        domain_id=domain_id,
        tags=["glossary", "term"],
        keywords=[term.lower(), "definition", "glossary"],
        related_metric_ids=related_metric_ids or [],
        **kwargs,
    )


def create_sql_example_item(
    title: str,
    sql: str,
    description: str,
    domain_id: str,
    related_metric_ids: list[str],
    **kwargs: Any,
) -> KnowledgeItem:
    """Create a SQL example knowledge item."""
    return KnowledgeItem(
        source_type=KnowledgeSourceType.SQL_EXAMPLE,
        title=title,
        content=f"{description}\n\n```sql\n{sql}\n```",
        domain_id=domain_id,
        tags=["sql", "example", "query"],
        keywords=["sql", "example", "query", "code"],
        related_metric_ids=related_metric_ids,
        permission_level=PermissionLevel.INTERNAL,
        **kwargs,
    )


def create_table_doc_item(
    table_name: str,
    description: str,
    columns: list[dict[str, str]],
    domain_id: str,
    **kwargs: Any,
) -> KnowledgeItem:
    """Create a table documentation knowledge item."""
    columns_text = "\n".join(
        f"- {c['name']}: {c.get('type', 'unknown')} - {c.get('description', '')}"
        for c in columns
    )
    content = f"{description}\n\n**Columns:**\n{columns_text}"

    return KnowledgeItem(
        source_type=KnowledgeSourceType.TABLE_DOCUMENTATION,
        title=f"Table: {table_name}",
        content=content,
        domain_id=domain_id,
        tags=["table", "documentation", table_name],
        keywords=[table_name.lower(), "table", "schema"],
        related_table_names=[table_name],
        related_column_names=[c["name"] for c in columns],
        **kwargs,
    )


# =============================================================================
# Global knowledge base
# =============================================================================


_knowledge_base: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    """Get global knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
        _initialize_default_knowledge(_knowledge_base)
    return _knowledge_base


def reset_knowledge_base() -> None:
    """Reset knowledge base (for testing)."""
    global _knowledge_base
    _knowledge_base = None


def _initialize_default_knowledge(kb: KnowledgeBase) -> None:
    """Initialize default knowledge items."""
    import uuid

    # Add finance metric definitions
    finance_metrics = [
        ("revenue", "Total Revenue", "Sum of all revenue transactions", "SUM(revenue)", "USD"),
        ("gross_profit", "Gross Profit", "Revenue minus cost of goods sold", "revenue - cogs", "USD"),
        ("gross_margin_rate", "Gross Margin Rate", "Gross profit as percentage of revenue", "gross_profit / revenue * 100", "%"),
        ("operating_expense", "Operating Expense", "Total operating expenses", "SUM(operating_expense)", "USD"),
        ("operating_profit", "Operating Profit", "EBIT - earnings before interest and taxes", "gross_profit - operating_expense", "USD"),
        ("budget_variance", "Budget Variance", "Difference between actual and budget", "actual - budget", "USD"),
    ]

    for metric_id, name, desc, formula, unit in finance_metrics:
        item = create_metric_definition_item(
            metric_id=metric_id,
            metric_name=name,
            description=desc,
            formula=formula,
            unit=unit,
            domain_id="finance",
            semantic_version="1.0.0",
        )
        kb.add_item(item)

    # Add sales metrics
    sales_metrics = [
        ("sales", "Sales", "Total sales amount", "SUM(sales_amount)", "USD"),
        ("orders", "Orders", "Count of orders", "COUNT(DISTINCT order_id)", "count"),
        ("average_selling_price", "Average Selling Price", "Average price per unit", "SUM(sales) / SUM(quantity)", "USD"),
        ("customer_count", "Customer Count", "Count of unique customers", "COUNT(DISTINCT customer_id)", "count"),
    ]

    for metric_id, name, desc, formula, unit in sales_metrics:
        item = create_metric_definition_item(
            metric_id=metric_id,
            metric_name=name,
            description=desc,
            formula=formula,
            unit=unit,
            domain_id="sales_operations",
            semantic_version="1.0.0",
        )
        kb.add_item(item)

    # Add supply chain metrics
    sc_metrics = [
        ("inventory", "Inventory", "Current inventory level", "SUM(inventory_quantity)", "units"),
        ("inventory_turnover", "Inventory Turnover", "Times inventory is replaced", "COGS / AVG(inventory)", "ratio"),
        ("stockout", "Stockout Events", "Count of stockout events", "COUNT(*) WHERE inventory = 0", "count"),
        ("lead_time", "Lead Time", "Days from order to receipt", "AVG(receipt_date - order_date)", "days"),
        ("fill_rate", "Fill Rate", "Orders filled from stock percentage", "filled_orders / total_orders * 100", "%"),
        ("supplier_otif", "Supplier OTIF", "On-time in-full delivery rate", "otif_orders / total_orders * 100", "%"),
    ]

    for metric_id, name, desc, formula, unit in sc_metrics:
        item = create_metric_definition_item(
            metric_id=metric_id,
            metric_name=name,
            description=desc,
            formula=formula,
            unit=unit,
            domain_id="supply_chain",
            semantic_version="1.0.0",
        )
        kb.add_item(item)

    # Add glossary terms
    glossary_terms = [
        ("Revenue", "Total income from sales before any deductions."),
        ("Gross Profit", "Revenue minus the direct cost of goods sold."),
        ("Operating Expense", "Day-to-day expenses required to run the business."),
        ("EBITDA", "Earnings before interest, taxes, depreciation, and amortization."),
        ("Fill Rate", "The percentage of customer orders fulfilled from available stock."),
        ("Lead Time", "The amount of time between placing an order and receiving it."),
        ("OTIF", "On-Time In-Full - a measure of supplier performance."),
    ]

    for term, definition in glossary_terms:
        item = create_glossary_item(
            term=term,
            definition=definition,
        )
        kb.add_item(item)

    # Add SQL examples
    sql_examples = [
        (
            "Revenue by Region",
            "SELECT region, SUM(revenue) AS total_revenue FROM fact_financials GROUP BY region",
            "Calculate total revenue grouped by region",
            "finance",
            ["revenue"],
        ),
        (
            "Gross Margin Calculation",
            "SELECT quarter, SUM(revenue) AS total_revenue, SUM(revenue - cogs) AS gross_profit, SUM(revenue - cogs) / SUM(revenue) AS margin_rate FROM fact_financials GROUP BY quarter",
            "Calculate gross margin by quarter",
            "finance",
            ["revenue", "gross_profit", "gross_margin_rate"],
        ),
    ]

    for title, sql, desc, domain, metrics in sql_examples:
        item = create_sql_example_item(
            title=title,
            sql=sql,
            description=desc,
            domain_id=domain,
            related_metric_ids=metrics,
        )
        kb.add_item(item)
