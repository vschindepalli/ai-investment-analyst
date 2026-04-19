"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

import type { FeatureBreakdown } from "@/lib/types";

interface Props {
  features: FeatureBreakdown;
  compact?: boolean;
}

export function FeatureRadar({ features, compact = false }: Props) {
  const data = [
    { axis: "Growth", value: features.growth },
    { axis: "Valuation", value: features.valuation },
    { axis: "Momentum", value: features.momentum },
    { axis: "Sentiment", value: features.sentiment },
  ];
  const height = compact ? 140 : 220;
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <RadarChart data={data} outerRadius={compact ? 50 : 82}>
          <PolarGrid stroke="#2a2a35" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: "#9a9aab", fontSize: 11 }}
          />
          <PolarRadiusAxis
            domain={[0, 1]}
            tick={false}
            axisLine={false}
          />
          <Radar
            dataKey="value"
            stroke="#10b981"
            fill="#10b981"
            fillOpacity={0.35}
            isAnimationActive={false}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
