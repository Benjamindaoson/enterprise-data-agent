from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    operatorId: int


class ChatRequest(BaseModel):
    sessionId: str
    message: str


class SummaryRequest(BaseModel):
    startDate: str | None = None
    endDate: str | None = None
    storeName: str | None = None


class TrendRequest(BaseModel):
    months: int = 6
    storeName: str | None = None
    title: str | None = None


class RefundRequest(BaseModel):
    startDate: str | None = None
    endDate: str | None = None
    storeName: str | None = None
    topN: int = 5


class AdRequest(BaseModel):
    startDate: str | None = None
    endDate: str | None = None
    storeName: str | None = None
    thresholdPercent: float = 35


class ReviewRequest(BaseModel):
    storeName: str | None = None
    days: int = 30


class ListingRequest(BaseModel):
    skuCode: str
    marketplace: str = "Amazon US"
    locale: str = "en-US"
    sellingPoint: str | None = None
