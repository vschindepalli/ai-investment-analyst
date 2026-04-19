"""/api/query endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.orchestrator.classifier import classify
from backend.orchestrator.router import route
from backend.schemas.request import QueryRequest
from backend.schemas.response import QueryResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    try:
        decision = classify(payload.query)
        handler = route(decision["intent"])
        return handler(
            query=payload.query,
            tickers=decision.get("tickers") or None,
            top_k=payload.top_k,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"pipeline failed: {e}") from e
