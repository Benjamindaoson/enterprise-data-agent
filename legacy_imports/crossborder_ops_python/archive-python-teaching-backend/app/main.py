from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import answer, stream_events
from app.db import check_db, get_db
from app.models import OperatorUser
from app.schemas import AdRequest, ChatRequest, ListingRequest, LoginRequest, RefundRequest, ReviewRequest, SummaryRequest, TrendRequest
from app.tools import business_trend_chart, high_acos_campaigns, refund_risks, summarize_business
from app.agent import listing_draft, review_insight


app = FastAPI(title="Crossborder Ops Agent Python")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/actuator/health")
def health():
    return {"status": "UP" if check_db() else "DOWN"}


@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(OperatorUser).where(OperatorUser.id == req.operatorId))
    if not user:
        raise HTTPException(status_code=400, detail="运营账号不存在")
    return {
        "token": f"python-demo-{user.id}",
        "username": user.name,
        "role": user.role,
        "operatorId": user.id,
        "storeId": user.store_id or "",
    }


@app.post("/auth/logout")
def logout():
    return {"message": "已退出登录"}


@app.post("/agent/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    return {"sessionId": req.sessionId, "content": answer(req.message, db)}


@app.post("/agent/chat/stream")
def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    text = answer(req.message, db)
    return StreamingResponse(stream_events(text), media_type="text/event-stream")


@app.delete("/agent/session/{session_id}")
def clear_session(session_id: str):
    return {"message": "session cleared", "sessionId": session_id}


@app.post("/test/tool/business-summary")
def test_business_summary(req: SummaryRequest | None = None, db: Session = Depends(get_db)):
    req = req or SummaryRequest()
    return summarize_business(db, req.startDate, req.endDate, req.storeName)


@app.post("/test/tool/business-trend-chart")
def test_business_chart(req: TrendRequest | None = None, db: Session = Depends(get_db)):
    req = req or TrendRequest()
    return business_trend_chart(db, req.months, req.storeName, req.title)


@app.post("/test/tool/refund-risks")
def test_refunds(req: RefundRequest | None = None, db: Session = Depends(get_db)):
    req = req or RefundRequest()
    return refund_risks(db, req.startDate, req.endDate, req.storeName, req.topN)


@app.post("/test/tool/high-acos-campaigns")
def test_ads(req: AdRequest | None = None, db: Session = Depends(get_db)):
    req = req or AdRequest()
    return high_acos_campaigns(db, req.startDate, req.endDate, req.storeName, req.thresholdPercent)


@app.post("/test/tool/review-insights")
def test_reviews(req: ReviewRequest | None = None, db: Session = Depends(get_db)):
    return review_insight(db)


@app.post("/test/tool/listing-draft")
def test_listing(req: ListingRequest, db: Session = Depends(get_db)):
    return listing_draft(db, req.skuCode)
