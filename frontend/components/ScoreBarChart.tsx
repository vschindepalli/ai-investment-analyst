"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { StockResult } from "@/lib/types";

export function ScoreBarChart({ stocks }: { stocks: StockResult[] }) {
  if (stocks.length < 2) return null;
  const data = stocks.map((s) => ({ ticker: s.ticker, score: s.score }));
  return (
    <div className="rounded-2xl border border-line bg-bg-card p-5">
      <h2 className="text-sm font-semibold text-ink">Ranking</h2>
      <p className="mt-0.5 text-xs text-ink-faint">Final weighted score</p>
      <div className="mt-3" style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid stroke="#22222c" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="ticker"
              stroke="#60606e"
              tick={{ fill: "#9a9aab", fontSize: 11, fontFamily: "ui-monospace" }}
              axisLine={{ stroke: "#2a2a35" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 1]}
              stroke="#60606e"
              tick={{ fill: "#9a9aab", fontSize: 11 }}
              axisLine={{ stroke: "#2a2a35" }}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.03)" }}
              contentStyle={{
                background: "#16161f",
                border: "1px solid #26262f",
                borderRadius: 8,
                color: "#e8e8ee",
                fontSize: 12,
              }}
              formatter={(v: number) => v.toFixed(3)}
            />
            <Bar dataKey="score" fill="#10b981" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
