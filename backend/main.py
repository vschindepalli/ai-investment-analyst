"""FastAPI entry point for the AI Investment Analyst backend.

Run locally:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.query import router as query_router
from backend.config import get_settings
from backend.services.embeddings import active_provider as embedding_provider
from backend.services.embeddings import embed_dim

settings = get_settings()

app = FastAPI(
    title="AI Investment Analyst",
    description=(
        "Hybrid AI financial intelligence: deterministic scoring + RAG + "
        "LLM-generated explanations."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "openai": settings.has_openai,
        "supabase": settings.has_supabase,
        "embeddings": {
            "provider": embedding_provider(),
            "dim": embed_dim(),
            "model": (
                settings.ollama_embed_model
                if embedding_provider() == "ollama"
                else settings.openai_embed_model
            ),
        },
    }
