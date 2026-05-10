"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/card";
import { RecoveryRing } from "@/components/recovery-ring";
import { SourceMetricCard, type Source } from "@/components/source-metric";
import { PeriodToggle, type Period } from "@/components/period-toggle";
import { differenceInDays, formatDistanceToNowStrict, parseISO } from "date-fns";

type DailyMetric = {
  date: string;
  hrv: number | null;
  rhr: number | null;
  sleep_score: number | null;
  sleep_hours: number | null;
  steps: number | null;
  recovery_score: number | null;
  strain: number | null;
  source: string | null;
};

type InBodyScan = {
  date: string;
  weight_lbs: number;
  bf_pct: number;
  skeletal_muscle_lbs: number | null;
};

type Workout = {
  date: string;
  exercise: string;
  workout_name: string | null;
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${MONTHS[parseInt(m, 10) - 1]} ${parseInt(d, 10)}, ${y}`;
}

function avgOf(values: (number | null | undefined)[]): number | null {
  const ns = values.filter((v): v is number => v != null && !isNaN(Number(v))).map(Number);
  if (ns.length === 0) return null;
  return ns.reduce((a, b) => a + b, 0) / ns.length;
}

function sumOf(values: (number | null | undefined)[]): number | null {
  const ns = values.filter((v): v is number => v != null && !isNaN(Number(v))).map(Number);
  if (ns.length === 0) return null;
  return ns.reduce((a, b) => a + b, 0);
}

const PERIOD_DAYS_MAP: Record<Period, number> = { D: 1, W: 7, M: 30, Y: 365 };

export function TodayClient({
  metrics,
  inbody,
  lastWorkout,
}: {
  metrics: DailyMetric[];
  inbody: InBodyScan[];
  lastWorkout: Workout | null;
}) {
  const [period, setPeriod] = useState<Period>("D");

  const sorted = useMemo(
    () => [...metrics].sort((a, b) => a.date.localeCompare(b.date)),
    [metrics]
  );

  // Compute aggregated value per metric for the selected period
  const agg = useMemo(() => {
    const days = PERIOD_DAYS_MAP[period];
    const slice = sorted.slice(-days);
    const prev = sorted.slice(-days * 2, -days);

    const get = (k: keyof DailyMetric) =>
      avgOf(slice.map((d) => d[k] as number | null));
    const getPrev = (k: keyof DailyMetric) =>
      avgOf(prev.map((d) => d[k] as number | null));
    const getSum = (k: keyof DailyMetric) =>
      sumOf(slice.map((d) => d[k] as number | null));
    const getSumPrev = (k: keyof DailyMetric) =>
      sumOf(prev.map((d) => d[k] as number | null));

    const stepsCurrent = period === "D" ? get("steps") : getSum("steps") != null && slice.length > 0 ? (getSum("steps") as number) / slice.length : null;
    const stepsPrev = period === "D" ? getPrev("steps") : getSumPrev("steps") != null && prev.length > 0 ? (getSumPrev("steps") as number) / prev.length : null;

    return {
      hrv: { current: get("hrv"), prev: getPrev("hrv") },
      rhr: { current: get("rhr"), prev: getPrev("rhr") },
      sleep_score: { current: get("sleep_score"), prev: getPrev("sleep_score") },
      sleep_hours: { current: get("sleep_hours"), prev: getPrev("sleep_hours") },
      steps: { current: stepsCurrent, prev: stepsPrev },
      recovery_score: { current: get("recovery_score"), prev: getPrev("recovery_score") },
      strain: { current: get("strain"), prev: getPrev("strain") },
    };
  }, [sorted, period]);

  // History for inline sparklines — 30 days, regardless of period
  const sparkSeries = useMemo(() => {
    const last30 = sorted.slice(-30);
    return {
      hrv: last30.map((d) => ({ date: d.date, value: d.hrv })),
      rhr: last30.map((d) => ({ date: d.date, value: d.rhr })),
      sleep_score: last30.map((d) => ({ date: d.date, value: d.sleep_score })),
      sleep_hours: last30.map((d) => ({ date: d.date, value: d.sleep_hours })),
      steps: last30.map((d) => ({ date: d.date, value: d.steps })),
      recovery_score: last30.map((d) => ({ date: d.date, value: d.recovery_score })),
      strain: last30.map((d) => ({ date: d.date, value: d.strain })),
    };
  }, [sorted]);

  const latest = sorted[sorted.length - 1];
  const latestInBody = inbody[inbody.length - 1];

  const fmt = (v: number | null, digits = 0): string =>
    v == null || isNaN(v) ? "—" : Number(v).toFixed(digits);
  const fmtInt = (v: number | null): string =>
    v == null || isNaN(v) ? "—" : Math.round(Number(v)).toLocaleString();

  const delta = (
    cur: number | null,
    prv: number | null,
    digits = 1,
    lowerIsBetter = false
  ) => {
    if (cur == null || prv == null) return null;
    const d = cur - prv;
    if (Math.abs(d) < 0.01) return null;
    return {
      value: `${d > 0 ? "+" : ""}${d.toFixed(digits)}`,
      positive: lowerIsBetter ? d < 0 : d > 0,
    };
  };

  const recoveryValue =
    period === "D"
      ? Math.round(latest?.recovery_score ?? 0)
      : Math.round(agg.recovery_score.current ?? 0);

  const strainValue =
    period === "D"
      ? latest?.strain ?? 0
      : agg.strain.current ?? 0;

  const periodLabel: Record<Period, string> = {
    D: "Today",
    W: "Last 7 days · avg",
    M: "Last 30 days · avg",
    Y: "Last 365 days · avg",
  };

  const lastSyncedAgo = latest ? formatDistanceToNowStrict(parseISO(latest.date), { addSuffix: true }) : "—";
  const lastWorkoutAgo = lastWorkout
    ? `${differenceInDays(new Date(), parseISO(lastWorkout.date))}d ago`
    : "—";

  return (
    <div className="space-y-8">
      {/* HEADER: period toggle + status pills */}
      <div className="flex flex-wrap items-center gap-3">
        <PeriodToggle value={period} onChange={setPeriod} />
        <span className="text-xs text-[var(--color-text-faint)]">
          {periodLabel[period]}
        </span>
        <div className="ml-auto flex flex-wrap items-center gap-2 text-xs">
          <Pill label="Last synced" value={lastSyncedAgo} dotColor="var(--color-recovery)" />
          {lastWorkout && (
            <Pill
              label="Last lift"
              value={`${lastWorkout.exercise} · ${lastWorkoutAgo}`}
              dotColor="var(--color-strain)"
            />
          )}
        </div>
      </div>

      {/* HERO: Recovery + summary metrics */}
      <section className="grid gap-6 lg:grid-cols-[auto_1fr]">
        <Card className="flex flex-col items-center justify-center bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-surface-2)]">
          <RecoveryRing value={recoveryValue} />
          <div className="mt-4 text-center">
            <div className="text-xs uppercase tracking-[0.25em] text-[var(--color-text-faint)]">
              Strain
            </div>
            <div className="metric-num mt-1 text-2xl font-semibold text-[var(--color-strain)]">
              {fmt(strainValue, 1)}
            </div>
          </div>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SourceMetricCard
            label="HRV"
            value={fmt(agg.hrv.current, 0)}
            unit="ms"
            accent="var(--color-recovery)"
            source="OURA"
            delta={delta(agg.hrv.current, agg.hrv.prev, 0)}
            hint="vs prev period"
            history={sparkSeries.hrv}
          />
          <SourceMetricCard
            label="Resting HR"
            value={fmt(agg.rhr.current, 0)}
            unit="bpm"
            accent="var(--color-alert)"
            source="WHOOP"
            delta={delta(agg.rhr.current, agg.rhr.prev, 0, true)}
            hint="vs prev period"
            history={sparkSeries.rhr}
          />
          <SourceMetricCard
            label="Sleep"
            value={fmt(agg.sleep_hours.current, 1)}
            unit="hr"
            accent="var(--color-sleep)"
            source="OURA"
            delta={delta(agg.sleep_hours.current, agg.sleep_hours.prev, 1)}
            hint={
              agg.sleep_score.current != null
                ? `score ${Math.round(agg.sleep_score.current)}`
                : undefined
            }
            history={sparkSeries.sleep_hours}
          />
          <SourceMetricCard
            label="Steps"
            value={fmtInt(agg.steps.current)}
            accent="var(--color-strain)"
            source="OURA"
            delta={delta(agg.steps.current, agg.steps.prev, 0)}
            hint={period === "D" ? "today" : "daily avg"}
            history={sparkSeries.steps}
          />
          <SourceMetricCard
            label="Weight"
            value={fmt(latestInBody?.weight_lbs ?? null, 1)}
            unit="lbs"
            source="INBODY"
            hint={latestInBody ? `scan ${formatDate(latestInBody.date)}` : undefined}
          />
          <SourceMetricCard
            label="Body Fat"
            value={fmt(latestInBody?.bf_pct ?? null, 1)}
            unit="%"
            accent="var(--color-warn)"
            source="INBODY"
            hint={
              latestInBody?.skeletal_muscle_lbs != null
                ? `SMM ${latestInBody.skeletal_muscle_lbs.toFixed(1)} lbs`
                : undefined
            }
          />
        </div>
      </section>

      {/* SECONDARY: Recovery + Strain charts (Whoop) */}
      <section className="grid gap-4 lg:grid-cols-2">
        <SourceMetricCard
          label="Recovery"
          value={fmt(agg.recovery_score.current, 0)}
          unit="%"
          accent="var(--color-recovery)"
          source="WHOOP"
          delta={delta(agg.recovery_score.current, agg.recovery_score.prev, 0)}
          hint="vs prev period"
          history={sparkSeries.recovery_score}
        />
        <SourceMetricCard
          label="Daily Strain"
          value={fmt(agg.strain.current, 1)}
          accent="var(--color-strain)"
          source="WHOOP"
          delta={delta(agg.strain.current, agg.strain.prev, 1)}
          hint="0–21 scale"
          history={sparkSeries.strain}
        />
      </section>
    </div>
  );
}

function Pill({
  label,
  value,
  dotColor,
}: {
  label: string;
  value: string;
  dotColor: string;
}) {
  return (
    <span className="flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1">
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: dotColor }} />
      <span className="text-[var(--color-text-faint)]">{label}</span>
      <span className="text-[var(--color-text)] tabular-nums">{value}</span>
    </span>
  );
}
