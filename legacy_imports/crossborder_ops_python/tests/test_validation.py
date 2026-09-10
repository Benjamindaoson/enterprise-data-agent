from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_summary_rejects_bad_date_before_business_logic():
    res = client.post("/test/tool/business-summary", json={"startDate": "not-a-date"})

    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_trend_rejects_out_of_range_months():
    res = client.post("/test/tool/business-trend-chart", json={"months": 99})

    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_chat_rejects_blank_message():
    res = client.post("/agent/chat", json={"sessionId": "s1", "message": ""})

    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"
