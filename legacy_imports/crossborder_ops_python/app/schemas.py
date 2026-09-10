from __future__ import annotations

from pydantic import BaseModel, Field


DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class LoginRequest(BaseModel):
    operatorId: int = Field(ge=1)
    loginCode: str | None = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    sessionId: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)


class SummaryRequest(BaseModel):
    startDate: str | None = Field(default=None, pattern=DATE_PATTERN)
    endDate: str | None = Field(default=None, pattern=DATE_PATTERN)
    storeName: str | None = Field(default=None, max_length=80)


class TrendRequest(BaseModel):
    months: int = Field(default=6, ge=1, le=18)
    storeName: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=120)


class RefundRequest(BaseModel):
    startDate: str | None = Field(default=None, pattern=DATE_PATTERN)
    endDate: str | None = Field(default=None, pattern=DATE_PATTERN)
    storeName: str | None = Field(default=None, max_length=80)
    topN: int = Field(default=5, ge=1, le=20)


class AdRequest(BaseModel):
    startDate: str | None = Field(default=None, pattern=DATE_PATTERN)
    endDate: str | None = Field(default=None, pattern=DATE_PATTERN)
    storeName: str | None = Field(default=None, max_length=80)
    thresholdPercent: float = Field(default=35, ge=1, le=500)


class ReviewRequest(BaseModel):
    storeName: str | None = Field(default=None, max_length=80)
    days: int = Field(default=30, ge=1, le=365)


class ListingRequest(BaseModel):
    skuCode: str = Field(min_length=1, max_length=80)
    marketplace: str = Field(default="Amazon US", max_length=40)
    locale: str = Field(default="en-US", max_length=20)
    sellingPoint: str | None = Field(default=None, max_length=300)
