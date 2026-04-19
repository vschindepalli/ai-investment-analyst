"""Dispatch from intent -> pipeline function."""
from __future__ import annotations

from typing import Callable

from backend.orchestrator import pipeline
from backend.schemas.response import QueryResponse


def route(intent: str) -> Callable[..., QueryResponse]:
    mapping = {
        "SCREENING": pipeline.screening_pipeline,
        "RESEARCH": pipeline.research_pipeline,
        "COMPARISON": pipeline.comparison_pipeline,
    }
    if intent not in mapping:
        raise ValueError(f"Unknown intent: {intent}")
    return mapping[intent]
