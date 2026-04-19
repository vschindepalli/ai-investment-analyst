"use client";

import { useState } from "react";

interface Props {
  onSubmit: (query: string) => void;
  loading?: boolean;
  defaultValue?: string;
}

const EXAMPLES = [
  "Top AI growth stocks right now",
  "Compare NVDA vs TSLA for AI exposure",
  "Why is META rallying?",
  "Undervalued large-cap tech with momentum",
];

export function SearchBar({ onSubmit, loading, defaultValue = "" }: Props) {
  const [value, setValue] = useState(defaultValue);

  const submit = (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setValue(trimmed);
    onSubmit(trimmed);
  };

  return (
    <div className="w-full">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
        className="group relative flex w-full items-center overflow-hidden rounded-2xl border border-line bg-bg-raised/80 shadow-lg backdrop-blur transition focus-within:border-accent/50 focus-within:shadow-glow"
      >
        <span className="pl-5 text-ink-faint" aria-hidden>
          <SearchIcon />
        </span>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask about a stock, strategy, or comparison…"
          className="flex-1 bg-transparent px-4 py-4 text-base text-ink placeholder:text-ink-faint focus:outline-none"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="mr-2 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-bg-hover disabled:text-ink-faint"
        >
          {loading ? (
            <>
              <Spinner /> Analyzing
            </>
          ) : (
            <>
              Analyze <ArrowIcon />
            </>
          )}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => submit(ex)}
            disabled={loading}
            className="rounded-full border border-line bg-bg-card px-3 py-1.5 text-xs text-ink-muted transition hover:border-accent/40 hover:text-ink disabled:opacity-60"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" strokeLinecap="round" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M5 12h14M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
