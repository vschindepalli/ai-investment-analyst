import type { ContextChunk } from "@/lib/types";

export function ContextList({ chunks }: { chunks: ContextChunk[] }) {
  if (chunks.length === 0) return null;
  return (
    <section className="rounded-2xl border border-line bg-bg-card p-5">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Retrieved context</h2>
        <span className="text-xs text-ink-faint">{chunks.length} passages</span>
      </header>
      <ul className="mt-3 space-y-3">
        {chunks.map((c, i) => (
          <li
            key={i}
            className="rounded-xl border border-line/70 bg-bg-raised/50 p-3"
          >
            <div className="mb-1 flex items-center gap-2 text-[11px] uppercase tracking-wider text-ink-faint">
              <span className="rounded bg-bg-hover px-1.5 py-0.5 text-ink-muted">
                {c.source}
              </span>
              {c.ticker ? (
                <span className="font-mono text-ink-muted">{c.ticker}</span>
              ) : null}
              {typeof c.similarity === "number" ? (
                <span className="ml-auto font-mono text-ink-faint">
                  sim {c.similarity.toFixed(3)}
                </span>
              ) : null}
            </div>
            <p className="text-sm leading-relaxed text-ink-muted">{c.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
