-- =====================================================================
-- AI Investment Analyst — Supabase schema
-- Run in the Supabase SQL editor. Requires the pgvector extension.
-- =====================================================================

create extension if not exists vector;

-- ---------- stocks ----------
create table if not exists stocks (
  ticker        text primary key,
  name          text not null,
  sector        text,
  industry      text,
  created_at    timestamptz default now()
);

-- ---------- stock_features ----------
-- One row per ticker, updated by the ingestion pipeline.
create table if not exists stock_features (
  ticker              text primary key references stocks(ticker) on delete cascade,
  revenue_growth      double precision,
  eps_growth          double precision,
  operating_margin    double precision,
  pe_ratio            double precision,
  peg_ratio           double precision,
  rsi                 double precision,
  return_3m           double precision,
  sentiment_score     double precision,
  updated_at          timestamptz default now()
);

-- ---------- news ----------
create table if not exists news (
  id            bigserial primary key,
  ticker        text references stocks(ticker) on delete set null,
  source        text,
  headline      text,
  body          text,
  published_at  timestamptz,
  created_at    timestamptz default now()
);

-- ---------- embeddings ----------
-- Generic chunk table for RAG. ``source`` = news | 10-K | earnings | ...
--
-- Vector dimension must match the active EMBEDDING_PROVIDER:
--   ollama / embeddinggemma          -> vector(768)   (default)
--   openai / text-embedding-3-small  -> vector(1536)
-- If you change providers you must drop and recreate this table + RPC.
create table if not exists embeddings (
  id          bigserial primary key,
  ticker      text references stocks(ticker) on delete set null,
  source      text not null,
  text        text not null,
  embedding   vector(768) not null,
  created_at  timestamptz default now()
);

create index if not exists embeddings_embedding_idx
  on embeddings using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- ---------- similarity search RPC ----------
create or replace function match_embeddings(
  query_embedding vector(768),
  match_count     int default 5
)
returns table (
  id          bigint,
  ticker      text,
  source      text,
  text        text,
  similarity  float
)
language sql stable
as $$
  select
    e.id,
    e.ticker,
    e.source,
    e.text,
    1 - (e.embedding <=> query_embedding) as similarity
  from embeddings e
  order by e.embedding <=> query_embedding
  limit match_count;
$$;
