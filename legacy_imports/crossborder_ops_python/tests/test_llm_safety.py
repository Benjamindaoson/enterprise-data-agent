from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.agent as agent
from app.seed import init_db, seed_demo_data


def test_llm_polish_preserves_original_tool_result(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = sessionmaker(engine)
    db = Session()
    seed_demo_data(db)
    monkeypatch.setattr(agent, "polish_with_llm", lambda question, tool_result: "AI 解读")

    text = agent.answer("分析最近 30 天的经营概览", db)

    assert "经营概览" in text
    assert "平均订单利润" in text
    assert "AI 解读" in text
