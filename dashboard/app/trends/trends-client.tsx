"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/card";
import { TrendArea, TrendLine, BarSeries } from "@/components/charts";
import { PeriodToggle, type Period } from "@/components/period-toggle";

type DailyMetric = {
  date: string;
  hrv: number | null;
  rhr: number | null;
  sleep_score: number | null;
  sleep_hours: number | null;
  steps: number | null;
  recovery_score: number | null;
  strain: number | null;
};

const PERIOD_DAYS_MAP: Record<Period, number> = { D: 14, W: 60, M: 180, Y: 365 };

export function TrendsClient({ metrics }: { metrics: DailyMetric[] }) {
  const [period, setPeriod] = useState<Period>("M");

  const sorted = useMemo(
    () => [...metrics].sort((a, b) => a.date.localeCompare(b.date)),
    [metrics]
  );

  // Coerce nulls to 0 for the chart components (their generic Datum type
  // doesn't accept null). The chart still skips zero-only days visually.
  const slice = useMemo(() => {
    return sorted.slice(-PERIOD_DAYS_MAP[period]).map((d) => ({
      date: d.date,
      hrv: d.hrv ?? 0,
      rhr: d.rhr ?? 0,
      sleep_score: d.sleep_score ?? 0,
      sleep_hours: d.sleep_hours ?? 0,
      steps: d.steps ?? 0,
      recovery_score: d.recovery_score ?? 0,
      strain: d.strain ?? 0,
    }));
  }, [sorted, period]);

  const avg = (key: keyof Omit<DailyMetric, "date">) => {
    const ns = slice
      .map((d) => d[key] as number)
      .filter((v) => v > 0 && !isNaN(v));
    if (ns.length === 0) return "—";
    return Math.round((ns.reduce((a, b) => a + b, 0) / ns.length) * 10) / 10;
  };

  const periodLabel: Record<Period, string> = {
    D: "Last 14 days",
    W: "Last 60 days",
    M: "Last 180 days",
    Y: "Last 365 days",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Trends</h1>
          <p className="mt-1 text-xs text-[var(--color-text-faint)]">
            {periodLabel[period]} · {slice.length} days of data
          </p>
        </div>
        <PeriodToggle value={period} onChange={setPeriod} />
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card title="HRV (ms)" hint={`avg ${avg("hrv")} ms`}>
          <TrendArea data={slice} dataKey="hrv" color="var(--color-recovery)" unit="ms" height={220} />
        </Card>
        <Card title="Resting HR (bpm)" hint={`avg ${avg("rhr")} bpm`}>
          <TrendLine data={slice} dataKey="rhr" color="var(--color-alert)" unit="bpm" height={220} />
        </Card>
        <Card title="Sleep (hours)" hint={`avg ${avg("sleep_hours")} h`}>
          <TrendArea data={slice} dataKey="sleep_hours" color="var(--color-sleep)" unit="h" height={220} />
        </Card>
        <Card title="Sleep Score" hint={`avg ${avg("sleep_score")}`}>
          <TrendLine data={slice} dataKey="sleep_score" color="var(--color-sleep)" height={220} />
        </Card>
        <Card title="Steps" hint={`avg ${typeof avg("steps") === "number" ? Number(avg("steps")).toLocaleString() : avg("steps")}`}>
          <BarSeries data={slice} dataKey="steps" color="var(--color-strain)" height={220} />
        </Card>
        <Card title="Recovery Score" hint={`avg ${avg("recovery_score")}`}>
          <TrendArea data={slice} dataKey="recovery_score" color="var(--color-recovery)" height={220} />
        </Card>
        <Card title="Strain" hint={`avg ${avg("strain")}`}>
          <TrendArea data={slice} dataKey="strain" color="var(--color-strain)" height={220} />
        </Card>
      </section>
    </div>
  );
}
