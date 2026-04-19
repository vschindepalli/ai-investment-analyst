import { IntentBadge } from "./IntentBadge";
import { ConfidenceMeter } from "./ConfidenceMeter";
import type { Intent } from "@/lib/types";

interface Props {
  intent: Intent;
  tickers: string[];
  explanation: string;
  confidence: number;
  meta?: Record<string, unknown>;
}

export function ExplanationPanel({
  intent,
  tickers,
  explanation,
  confidence,
  meta,
}: Props) {
  const llm = Boolean(meta?.llm);
  const supabase = Boolean(meta?.supabase);
  return (
    <section className="rounded-2xl border border-line bg-bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <IntentBadge intent={intent} />
          {tickers.map((t) => (
            <span
              key={t}
              className="rounded-md bg-bg-raised px-2 py-0.5 font-mono text-xs text-ink-muted"
            >
              {t}
            </span>
          ))}
        </div>
        <ConfidenceMeter value={confidence} />
      </div>

      <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-ink">
        {explanation}
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-3 text-[11px] text-ink-faint">
        <Flag label="LLM" on={llm} />
        <Flag label="Supabase" on={supabase} />
        <span>
          Scores are deterministic. The LLM only interprets them — it never
          computes numbers.
        </span>
      </div>
    </section>
  );
}

function Flag({ label, on }: { label: string; on: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`h-1.5 w-1.5 rounded-full ${on ? "bg-accent" : "bg-ink-faint/60"}`}
      />
      {label}: {on ? "live" : "mock"}
    </span>
  );
}
