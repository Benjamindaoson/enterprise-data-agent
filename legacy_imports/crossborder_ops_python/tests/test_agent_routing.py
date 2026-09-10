from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent import route_tool
from app.seed import init_db, seed_demo_data


def seeded_db():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = sessionmaker(engine)
    db = Session()
    seed_demo_data(db)
    return db


def test_chart_intent_routes_to_visual_payload_with_chinese_question():
    text = route_tool("画出最近 6 个月净销售额和利润趋势图", seeded_db())

    assert text.startswith("VISUAL_PAYLOAD:")


def test_chart_intent_routes_to_visual_payload_with_ascii_question():
    text = route_tool("show the 6 month sales and profit trend chart", seeded_db())

    assert text.startswith("VISUAL_PAYLOAD:")
