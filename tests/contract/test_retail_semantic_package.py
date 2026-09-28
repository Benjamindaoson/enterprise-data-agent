from pathlib import Path

from eiw.semantic.package import load_semantic_package

PACKAGE = Path("semantic_packages/retail_complete_journey/semantic-package.yaml")


def test_retail_semantic_package_has_ba_metrics_and_dimensions() -> None:
    package = load_semantic_package(PACKAGE)

    assert package.package.id == "retail_complete_journey"
    assert {metric.id for metric in package.metrics} >= {
        "sales_value",
        "units",
        "baskets",
        "average_basket_value",
    }
    assert {dimension.id for dimension in package.dimensions} >= {
        "store",
        "product",
        "commodity",
        "household",
        "display",
    }


def test_retail_semantic_package_marks_merchandising_as_non_causal_by_default() -> None:
    package = load_semantic_package(PACKAGE)
    rules = {rule["id"]: rule["description"] for rule in package.business_rules}

    assert "association" in rules["merchandising_association_not_causality"].lower()
