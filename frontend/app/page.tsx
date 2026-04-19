"use client";

import { useCallback, useRef, useState } from "react";

import { ContextList } from "@/components/ContextList";
import { ExplanationPanel } from "@/components/ExplanationPanel";
import { ScoreBarChart } from "@/components/ScoreBarChart";
import { SearchBar } from "@/components/SearchBar";
import { StockCard } from "@/components/StockCard";
import { runQuery } from "@/lib/api";
import type { QueryResponse } from "@/lib/types";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<QueryResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const submit = useCallback(async (query: string) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setError(null);
    try {
      const resp = await runQuery({ query, top_k: 5 }, ctrl.signal);
      setData(resp);
    } catch (e: unknown) {
      if ((e as Error).name === "AbortError") return;
      setError((e as Error).message || "Something went wrong.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-6 pb-24 pt-10 sm:pt-16">
      <Header />

      <SearchBar onSubmit={submit} loading={loading} />

      {error ? (
        <div className="rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      {loading && !data ? <LoadingState /> : null}

      {data ? <Results data={data} /> : !loading ? <EmptyState /> : null}

      <footer className="mt-auto pt-8 text-center text-xs text-ink-faint">
        Deterministic scoring · pgvector retrieval · LLM explanation only
      </footer>
    </main>
  );
}

function Header() {
  return (
    <header className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-accent ring-1 ring-accent/30">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 17l6-6 4 4 8-8" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M14 7h7v7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            AI Investment Analyst
          </h1>
          <p className="text-xs text-ink-muted">
            Deterministic scoring · Retrieval-augmented context · LLM-generated
            explanations
          </p>
        </div>
      </div>
    </header>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-bg-card/40 p-10 text-center">
      <h2 className="text-base font-medium text-ink">Ask anything above</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-ink-muted">
        Try a screening query (“best AI growth picks”), a research question
        (“why is META rallying?”), or a head-to-head comparison (“NVDA vs
        AAPL”).
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="h-40 animate-pulse rounded-2xl border border-line bg-bg-card/60"
        />
      ))}
    </div>
  );
}

function Results({ data }: { data: QueryResponse }) {
  return (
    <div className="flex flex-col gap-6">
      <ExplanationPanel
        intent={data.intent}
        tickers={data.tickers}
        explanation={data.explanation}
        confidence={data.confidence}
        meta={data.meta}
      />

      {data.results.length > 0 ? (
        <>
          {data.intent !== "RESEARCH" ? (
            <ScoreBarChart stocks={data.results} />
          ) : null}

          <section className="grid gap-4 md:grid-cols-2">
            {data.results.map((s, i) => (
              <StockCard key={s.ticker} stock={s} rank={i + 1} />
            ))}
          </section>
        </>
      ) : null}

      <ContextList chunks={data.context} />
    </div>
  );
}
