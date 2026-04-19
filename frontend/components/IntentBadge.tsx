import type { Intent } from "@/lib/types";

const STYLES: Record<Intent, { label: string; dot: string; ring: string }> = {
  SCREENING: {
    label: "Screening",
    dot: "bg-emerald-400",
    ring: "ring-emerald-500/30 text-emerald-300",
  },
  RESEARCH: {
    label: "Research",
    dot: "bg-sky-400",
    ring: "ring-sky-500/30 text-sky-300",
  },
  COMPARISON: {
    label: "Comparison",
    dot: "bg-violet-400",
    ring: "ring-violet-500/30 text-violet-300",
  },
};

export function IntentBadge({ intent }: { intent: Intent }) {
  const s = STYLES[intent];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full bg-bg-raised px-3 py-1 text-xs font-medium ring-1 ${s.ring}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}
