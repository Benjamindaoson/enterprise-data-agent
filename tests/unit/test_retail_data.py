import csv
from pathlib import Path

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


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_completejourney_cc0_lowercase_schema_is_supported(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "transactions.csv",
        [
            {
                "household_id": "1",
                "store_id": "10",
                "basket_id": "100",
                "product_id": "1000",
                "quantity": 2,
                "sales_value": 8.0,
                "retail_disc": 0.5,
                "coupon_disc": 0.0,
                "coupon_match_disc": 0.0,
                "week": 1,
                "transaction_timestamp": "2017-01-01",
            },
            {
                "household_id": "1",
                "store_id": "10",
                "basket_id": "101",
                "product_id": "1000",
                "quantity": 1,
                "sales_value": 5.0,
                "retail_disc": 0.0,
                "coupon_disc": 0.0,
                "coupon_match_disc": 0.0,
                "week": 2,
                "transaction_timestamp": "2017-01-08",
            },
        ],
    )
    _write_csv(
        tmp_path / "products.csv",
        [
            {
                "product_id": "1000",
                "manufacturer": "1",
                "department": "GROCERY",
                "brand": "National",
                "commodity": "PASTA",
                "sub_commodity": "DRY PASTA",
                "size": "16 OZ",
            }
        ],
    )
    _write_csv(
        tmp_path / "promotions.csv",
        [
            {
                "product_id": "1000",
                "store_id": "10",
                "display_location": "3",
                "mailer_location": "A",
                "week": 2,
            }
        ],
    )

    data = RetailDataEngine.from_complete_journey(tmp_path)
    status = data.status()

    assert status["counts"]["retail_transactions"] == 2
    assert status["counts"]["retail_products"] == 1
    assert status["counts"]["retail_promotions"] == 1
    assert status["min_week"] == 1
    assert status["max_week"] == 2
    assert data.promotion_performance([2])[0]["display_location"] == "3"


def test_cross_dimension_scan_includes_top_negative_driver() -> None:
    data = RetailDataEngine.demo()
    rows = data.cross_dimension_scan([7, 8], [5, 6], limit=3)
    gold = data.query_readonly(
        """
        WITH cur AS (
            SELECT t.store_id, p.commodity, SUM(t.sales_value) AS sales
            FROM retail_transactions t
            JOIN retail_products p ON p.product_id = t.product_id
            WHERE t.week_no IN (7, 8)
            GROUP BY 1, 2
        ),
        prev AS (
            SELECT t.store_id, p.commodity, SUM(t.sales_value) AS sales
            FROM retail_transactions t
            JOIN retail_products p ON p.product_id = t.product_id
            WHERE t.week_no IN (5, 6)
            GROUP BY 1, 2
        )
        SELECT
            COALESCE(cur.store_id, prev.store_id) AS store_id,
            COALESCE(cur.commodity, prev.commodity) AS commodity,
            COALESCE(cur.sales, 0) - COALESCE(prev.sales, 0) AS sales_delta
        FROM cur
        FULL OUTER JOIN prev USING(store_id, commodity)
        WHERE COALESCE(cur.sales, 0) - COALESCE(prev.sales, 0) < 0
        ORDER BY ABS(sales_delta) DESC
        LIMIT 1
        """
    )

    assert gold
    expected = (gold[0]["store_id"], gold[0]["commodity"])
    observed = {(row["store_id"], row["commodity"]) for row in rows}
    assert expected in observed
