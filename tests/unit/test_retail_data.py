from eiw.retail.data import RetailDataEngine


def test_demo_engine_exposes_business_scale_contracts() -> None:
    data = RetailDataEngine.demo()
    status = data.status()

    assert status["counts"]["retail_transactions"] > 0
    assert status["counts"]["retail_products"] == 6
    assert status["max_week"] == 8


def test_demo_period_has_intentional_sales_decline_and_contributors() -> None:
    data = RetailDataEngine.demo()
    overview = data.overview([7, 8], [5, 6])
    rows = data.contribution("store", [7, 8], [5, 6], limit=10)

    assert overview["sales_change_pct"] < 0
    assert any(str(row["segment"]) in {"3", "4"} and row["delta"] < 0 for row in rows)


def test_merchandising_and_basket_queries_are_executable() -> None:
    data = RetailDataEngine.demo()

    merchandising = data.promotion_performance([7, 8])
    affinity = data.basket_affinity([7, 8])

    assert merchandising
    assert {row["display_location"] for row in merchandising} >= {"FRONT END CAP", "NO DISPLAY"}
    assert affinity


def test_cross_dimension_scan_and_price_volume_decomposition() -> None:
    data = RetailDataEngine.demo()

    scan = data.cross_dimension_scan([7, 8], [5, 6], limit=20)
    decomposition = data.price_volume_decomposition([7, 8], [5, 6], limit=10)

    assert scan
    assert any(
        row["store_id"] in {3, 4}
        and row["commodity"] == "SUN CARE"
        and row["sales_delta"] < 0
        for row in scan
    )
    assert decomposition
    assert all(abs(float(row["reconciliation_error"])) < 1e-8 for row in decomposition)
