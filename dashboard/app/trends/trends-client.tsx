"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/card";
import { TrendChart } from "@/components/charts";
import { cn } from "@/lib/cn";
import { avg } from "@/lib/health";

type DailyMetric = {
  date: string;
  hrv: number | null;
  rhr: number | null;
  sleep_hours: number | null;
  steps: number | null;
  recovery_score: number | null;
  strain: number | null;
};
type Key = Exclude<keyof DailyMetric, "date">;

const RANGES = [
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "1 year", days: 365 },
];

// One source per metric, never mixed (see health-agent/supabase_sync.py)
const METRICS: { key: Key; title: string; unit: string; digits: number; source: string; about: string; goal?: number }[] = [
  { key: "recovery_score", title: "Recovery", unit: "%", digits: 0, source: "Whoop", about: "How ready your body is. 67% and up is good." },
  { key: "sleep_hours", title: "Sleep", unit: "h", digits: 1, source: "Oura", about: "Time asleep. Your goal is 7.5 hours.", goal: 7.5 },
  { key: "hrv", title: "HRV", unit: "ms", digits: 0, source: "Oura", about: "Heart rate variability. Higher usually means better recovered." },
  { key: "rhr", title: "Resting heart rate", unit: "bpm", digits: 0, source: "Oura", about: "Lowest heart rate overnight. Lower is usually fitter." },
  { key: "steps", title: "Steps", unit: "steps", digits: 0, source: "Oura", about: "Your goal is 8,000 a day.", goal: 8000 },
  { key: "strain", title: "Strain", unit: "", digits: 1, source: "Whoop", about: "The day's total effort, on a 0 to 21 scale." },
];

export function TrendsClient({ metrics }: { metrics: DailyMetric[] }) {
  const [days, setDays] = useState(90);
  const slice = useMemo(
    () => [...metrics].sort((a, b) => a.date.localeCompare(b.date)).slice(-days),
    [metrics, days]
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="space-y-3">
        <div>
          <h1 className="text-[28px] font-semibold tracking-[-0.02em] sm:text-[34px]">Trends</h1>
          <p className="mt-1 text-[15px] text-[var(--color-text-dim)]">
            Dots are single days. The line is your 7-day average, which shows the real direction.
          </p>
        </div>
        <div className="inline-flex rounded-full bg-[var(--color-surface-2)] p-0.5" role="tablist" aria-label="Time range">
          {RANGES.map((r) => (
            <button
              key={r.days}
              role="tab"
              aria-selected={days === r.days}
              onClick={() => setDays(r.days)}
              className={cn(
                "rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors",
                days === r.days ? "bg-[var(--color-surface)] text-[var(--color-text)] shadow-sm" : "text-[var(--color-text-dim)]"
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </header>

      {METRICS.map((m) => {
        const points = slice.map((d) => ({ date: d.date, value: d[m.key] == null || d[m.key] === 0 ? null : Number(d[m.key]) }));
        const mean = avg(points.map((p) => p.value));
        if (mean == null) return null; // nothing to show for this source yet
        return (
          <Card key={m.key} title={m.title} hint={`${m.source} · average ${mean.toLocaleString(undefined, { minimumFractionDigits: m.digits, maximumFractionDigits: m.digits })}${m.unit === "%" ? "%" : m.unit && m.unit !== "steps" ? ` ${m.unit}` : ""}`}>
            <p className="-mt-2 mb-3 text-[13px] text-[var(--color-text-dim)]">{m.about}</p>
            <TrendChart points={points} unit={m.unit} digits={m.digits} goal={m.goal} />
          </Card>
        );
      })}
    </div>
  );
}
