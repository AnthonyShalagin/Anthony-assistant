"use client";

import { cn } from "@/lib/cn";
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type HistoryPoint = { date: string; value: number; status: string };

const STATUS_COLOR: Record<string, string> = {
  optimal: "var(--color-recovery)",
  normal: "var(--color-strain)",
  high: "var(--color-alert)",
  low: "var(--color-warn)",
};

export function BiomarkerCard({
  marker,
  value,
  unit,
  ref_low,
  ref_high,
  status,
  history,
}: {
  marker: string;
  value: number;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  status: "optimal" | "normal" | "high" | "low" | string;
  history: HistoryPoint[];
}) {
  const statusColor = STATUS_COLOR[status] ?? "var(--color-text)";
  const statusLabel = status.toUpperCase();

  const showHistory = history.length >= 2;
  const prev = history.length >= 2 ? history[history.length - 2] : null;
  const delta = prev ? value - prev.value : null;
  const deltaUp = delta != null && delta > 0;
  const deltaDown = delta != null && delta < 0;

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-medium text-[var(--color-text)]">{marker}</div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="metric-num text-2xl font-semibold" style={{ color: statusColor }}>
              {value}
            </span>
            <span className="text-xs text-[var(--color-text-faint)]">{unit}</span>
          </div>
        </div>
        <span
          className="rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wider"
          style={{ background: `${statusColor}22`, color: statusColor }}
        >
          {statusLabel}
        </span>
      </div>

      {/* History chart */}
      {showHistory && (
        <div className="mt-3 -mx-1">
          <ResponsiveContainer width="100%" height={64}>
            <AreaChart data={history} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
              <defs>
                <linearGradient id={`bg-${marker.replace(/\W/g, "")}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={statusColor} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={statusColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" hide />
              <YAxis
                hide
                domain={[
                  (dataMin: number) => {
                    const refMin = Math.min(...[ref_low, ref_high].filter((x): x is number => x != null));
                    const m = Math.min(dataMin, isFinite(refMin) ? refMin : dataMin);
                    return m * 0.9;
                  },
                  (dataMax: number) => {
                    const refMax = Math.max(...[ref_low, ref_high].filter((x): x is number => x != null));
                    const m = Math.max(dataMax, isFinite(refMax) ? refMax : dataMax);
                    return m * 1.1;
                  },
                ]}
              />
              {ref_low != null && (
                <ReferenceLine y={ref_low} stroke="#3a3a3a" strokeDasharray="2 3" />
              )}
              {ref_high != null && (
                <ReferenceLine y={ref_high} stroke="#3a3a3a" strokeDasharray="2 3" />
              )}
              <Area
                type="monotone"
                dataKey="value"
                stroke={statusColor}
                strokeWidth={1.5}
                fill={`url(#bg-${marker.replace(/\W/g, "")})`}
                dot={{ r: 2, fill: statusColor, strokeWidth: 0 }}
                activeDot={{ r: 3 }}
              />
              <Tooltip
                cursor={{ stroke: "#262626" }}
                contentStyle={{
                  background: "#0a0a0a",
                  border: "1px solid #262626",
                  borderRadius: 6,
                  fontSize: 11,
                  padding: "4px 8px",
                  color: "#f5f5f5",
                }}
                labelStyle={{ color: "#a1a1a1", fontSize: 10 }}
                formatter={(v) => [`${v}${unit ? " " + unit : ""}`, marker] as [string, string]}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="mt-1 flex justify-between text-[9px] tabular-nums text-[var(--color-text-faint)]">
            <span>{history[0].date.slice(0, 7)}</span>
            <span>{history[history.length - 1].date.slice(0, 7)}</span>
          </div>
        </div>
      )}

      {/* Reference range bar (always shown) */}
      <div className="mt-3 flex items-center justify-between text-[10px] tabular-nums text-[var(--color-text-faint)]">
        <span>
          {ref_low != null ? `≥ ${ref_low}` : ""}
          {ref_low != null && ref_high != null ? " · " : ""}
          {ref_high != null ? `≤ ${ref_high}` : ""}
          {ref_low == null && ref_high == null ? "no range" : ""}
        </span>
        {delta != null && (
          <span className={cn(deltaUp ? "text-[var(--color-warn)]" : deltaDown ? "text-[var(--color-recovery)]" : "")}>
            {deltaUp ? "▲" : deltaDown ? "▼" : "—"} {Math.abs(delta).toFixed(1)} vs {prev!.date.slice(0, 7)}
          </span>
        )}
      </div>
    </div>
  );
}
