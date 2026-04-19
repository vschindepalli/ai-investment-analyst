from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Intent = Literal["SCREENING", "RESEARCH", "COMPARISON"]


class FeatureBreakdown(BaseModel):
    growth: float
    valuation: float
    momentum: float
    sentiment: float


class StockResult(BaseModel):
    ticker: str
    name: str | None = None
    score: float
    features: FeatureBreakdown
    rationale: str | None = None


class ContextChunk(BaseModel):
    source: str
    ticker: str | None = None
    text: str
    similarity: float | None = None


class QueryResponse(BaseModel):
    intent: Intent
    tickers: list[str] = Field(default_factory=list)
    results: list[StockResult] = Field(default_factory=list)
    context: list[ContextChunk] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    meta: dict[str, Any] = Field(default_factory=dict)
