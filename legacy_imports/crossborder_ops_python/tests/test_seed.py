from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import CommerceOrder, OperatorUser, Store
from app.seed import init_db, seed_demo_data
from app.tools import summarize_business


def test_seed_demo_data_is_idempotent_and_supports_core_summary():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = sessionmaker(engine)

    with Session() as db:
        seed_demo_data(db)
        seed_demo_data(db)

        assert db.scalar(select(Store).where(Store.name == "Amazon US Store"))
        assert db.scalar(select(OperatorUser).where(OperatorUser.id == 3))
        assert db.query(CommerceOrder).count() >= 8
        assert "平均订单利润" in summarize_business(db, "2026-06-01", "2026-07-05")
