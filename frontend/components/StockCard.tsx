import type { StockResult } from "@/lib/types";
import { FeatureRadar } from "./FeatureRadar";

interface Props {
  stock: StockResult;
  rank: number;
}

const FEATURE_ORDER: Array<keyof StockResult["features"]> = [
  "growth",
  "valuation",
  "momentum",
  "sentiment",
];

export function StockCard({ stock, rank }: Props) {
  const scorePct = Math.round(stock.score * 100);
  return (
    <article className="group flex flex-col gap-4 rounded-2xl border border-line bg-bg-card p-5 transition hover:border-accent/30 hover:bg-bg-hover">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-md bg-bg-raised px-1.5 font-mono text-xs text-ink-muted">
              #{rank}
            </span>
            <h3 className="font-mono text-lg font-semibold tracking-wide text-ink">
              {stock.ticker}
            </h3>
          </div>
          {stock.name ? (
            <p className="mt-1 text-sm text-ink-muted">{stock.name}</p>
          ) : null}
        </div>
        <div className="text-right">
          <div className="font-mono text-2xl font-semibold text-ink">
            {stock.score.toFixed(2)}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-ink-faint">
            score
          </div>
        </div>
      </header>

      <div className="grid grid-cols-[1fr_auto] gap-4">
        <div className="flex flex-col gap-2">
          {FEATURE_ORDER.map((key) => {
            const v = stock.features[key];
            const pct = Math.round(v * 100);
            return (
              <div key={key} className="flex items-center gap-3">
                <span className="w-20 text-xs capitalize text-ink-muted">
                  {key}
                </span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-bg-raised">
                  <div
                    className="h-full bg-accent/80"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-10 text-right font-mono text-xs text-ink">
                  {v.toFixed(2)}
                </span>
              </div>
            );
          })}
        </div>
        <div className="hidden w-44 sm:block">
          <FeatureRadar features={stock.features} compact />
        </div>
      </div>

      {stock.rationale ? (
        <p className="rounded-lg border border-line/60 bg-bg-raised/60 px-3 py-2 text-xs text-ink-muted">
          {stock.rationale}
        </p>
      ) : null}

      <footer className="flex items-center justify-between text-[11px] text-ink-faint">
        <span>weighted: 0.35 growth · 0.25 val · 0.25 mom · 0.15 sent</span>
        <span className="font-mono">{scorePct}%</span>
      </footer>
    </article>
  );
}
