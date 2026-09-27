"use client";

import { ComposedChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const monthDay = (iso: string) => `${MONTHS[parseInt(iso.slice(5, 7), 10) - 1]} ${parseInt(iso.slice(8, 10), 10)}`;
const monthOnly = (iso: string) => MONTHS[parseInt(iso.slice(5, 7), 10) - 1];

export type Point = { date: string; value: number | null };

/** Trailing 7-day mean, skipping missing days. */
function rolling(points: Point[]): (number | null)[] {
  return points.map((_, i) => {
    const w = points.slice(Math.max(0, i - 6), i + 1).map((p) => p.value).filter((v): v is number => v != null);
    return w.length >= 3 ? w.reduce((a, b) => a + b, 0) / w.length : null;
  });
}

function fmtAxis(v: number): string {
  if (Math.abs(v) >= 1000) return `${Math.round(v / 100) / 10}k`;
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}

/**
 * One metric: each day as a faint dot, the 7-day average as a solid line.
 * The y-axis fits the data (never forced to zero) so real change is visible.
 */
export function TrendChart({
  points,
  unit,
  digits = 0,
  goal,
  height = 180,
}: {
  points: Point[];
  unit: string;
  digits?: number;
  goal?: number;
  height?: number;
}) {
  const avg = rolling(points);
  const data = points.map((p, i) => ({ date: p.date, day: p.value, avg: avg[i] }));
  const long = points.length > 120;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 4, left: -12, bottom: 0 }}>
        <CartesianGrid stroke="var(--color-border)" vertical={false} />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          fontSize={11}
          stroke="var(--color-text-dim)"
          tickFormatter={long ? monthOnly : monthDay}
          minTickGap={36}
        />
        <YAxis
          domain={[(min: number) => Math.floor(Math.min(min, goal ?? min) * 0.95), (max: number) => Math.ceil(Math.max(max, goal ?? max) * 1.03)]}
          tickCount={3}
          tickLine={false}
          axisLine={false}
          fontSize={11}
          stroke="var(--color-text-dim)"
          width={44}
          tickFormatter={fmtAxis}
          allowDecimals={digits > 0}
        />
        <Tooltip
          cursor={{ stroke: "var(--color-border)" }}
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 10,
            fontSize: 13,
            color: "var(--color-text)",
          }}
          labelFormatter={(l) => monthDay(String(l))}
          formatter={(v, name) => [
            v == null ? "–" : `${Number(v).toFixed(digits)} ${unit}`,
            name === "avg" ? "7-day average" : "That day",
          ]}
        />
        {goal != null && (
          <Line dataKey={() => goal} stroke="var(--color-good)" strokeDasharray="4 4" strokeWidth={1} dot={false} activeDot={false} legendType="none" isAnimationActive={false} />
        )}
        <Line
          dataKey="day"
          stroke="transparent"
          dot={{ r: 1.6, fill: "var(--color-chart-soft)", stroke: "none" }}
          activeDot={{ r: 3.5, fill: "var(--color-text-dim)" }}
          isAnimationActive={false}
        />
        <Line dataKey="avg" stroke="var(--color-chart)" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
