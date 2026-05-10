"use client";

import { cn } from "@/lib/cn";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type Source = "OURA" | "WHOOP" | "INBODY" | "STRONG";

const SOURCE_COLOR: Record<Source, string> = {
  OURA: "#9b6dff",  // Oura purple-ish (matches our sleep accent)
  WHOOP: "#0093ff", // Whoop blue
  INBODY: "#ffb020",// InBody amber
  STRONG: "#00ff94",// Strong green
};

export function SourceMetricCard({
  label,
  value,
  unit,
  delta,
  hint,
  source,
  accent,
  history,
  formatTooltip,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  delta?: { value: string; positive: boolean } | null;
  hint?: string;
  source?: Source;
  accent?: string;
  /** Last N days of values for the inline sparkline. */
  history?: { date: string; value: number | null }[];
  formatTooltip?: (v: number) => string;
}) {
  const valueColor = accent ?? "var(--color-text)";
  const sourceColor = source ? SOURCE_COLOR[source] : null;
  const cleanHistory = (history ?? []).filter((h) => h.value != null && !isNaN(Number(h.value)));

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
          {label}
        </div>
        {source && sourceColor && (
          <span
            className="rounded px-1.5 py-0.5 text-[9px] font-semibold tracking-wider"
            style={{ background: `${sourceColor}22`, color: sourceColor }}
          >
            {source}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span
          className="metric-num text-4xl font-semibold leading-none"
          style={{ color: valueColor }}
        >
          {value ?? "—"}
        </span>
        {unit && value != null && (
          <span className="text-sm text-[var(--color-text-faint)]">{unit}</span>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs">
        {delta ? (
          <span
            className={cn(
              "tabular-nums",
              delta.positive ? "text-[var(--color-recovery)]" : "text-[var(--color-alert)]"
            )}
          >
            {delta.positive ? "▲" : "▼"} {delta.value}
          </span>
        ) : (
          <span />
        )}
        {hint && <span className="text-[var(--color-text-faint)]">{hint}</span>}
      </div>

      {cleanHistory.length >= 2 && (
        <div className="-mx-1 mt-3 h-10">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={cleanHistory} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
              <defs>
                <linearGradient id={`smc-${label.replace(/\W/g, "")}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={valueColor} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={valueColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" hide />
              <YAxis hide domain={["auto", "auto"]} />
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
                formatter={(v) => {
                  const n = Number(v);
                  return [formatTooltip ? formatTooltip(n) : `${n}${unit ? " " + unit : ""}`, label] as [string, string];
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={valueColor}
                strokeWidth={1.5}
                fill={`url(#smc-${label.replace(/\W/g, "")})`}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
