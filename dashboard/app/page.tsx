import { Card, MetricCard } from "@/components/card";
import { TrendArea, BarSeries } from "@/components/charts";
import { RecoveryRing } from "@/components/recovery-ring";
import { fetchDailyMetrics, fetchInBody, fetchSleepDetails } from "@/lib/data";
import { getSleepDetails as mockSleep } from "@/lib/mock";

export const dynamic = "force-dynamic";

export default async function TodayPage() {
  const [days, sleep, inbody] = await Promise.all([
    fetchDailyMetrics(30),
    fetchSleepDetails(7),
    fetchInBody(),
  ]);
  const today = days[days.length - 1];
  const yesterday = days[days.length - 2];
  const latestInBody = inbody[inbody.length - 1];

  // Coalesce missing/nullable real-world data
  const num = (v: number | null | undefined): number | null =>
    v == null || isNaN(Number(v)) ? null : Number(v);
  const fmt = (v: number | null | undefined, digits = 1) =>
    v == null ? "—" : Number(v).toFixed(digits);
  const fmtInt = (v: number | null | undefined) =>
    v == null ? "—" : Number(v).toLocaleString();

  const delta = (a: number | null | undefined, b: number | null | undefined, unit = "") => {
    const an = num(a);
    const bn = num(b);
    if (an == null || bn == null) return undefined;
    const d = an - bn;
    return {
      value: `${d >= 0 ? "+" : ""}${d.toFixed(unit === "%" || unit === "h" ? 1 : 0)}${unit}`,
      positive: d >= 0,
    };
  };

  const last7 = days.slice(-7);

  return (
    <div className="space-y-8">
      {/* Hero: Recovery + summary */}
      <section className="grid gap-6 lg:grid-cols-[auto_1fr]">
        <Card className="flex flex-col items-center justify-center bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-surface-2)]">
          <RecoveryRing value={num(today.recovery_score) ?? 0} />
          <div className="mt-4 text-center">
            <div className="text-xs uppercase tracking-[0.25em] text-[var(--color-text-faint)]">
              Strain
            </div>
            <div className="metric-num mt-1 text-2xl font-semibold text-[var(--color-strain)]">
              {fmt(today.strain)}
            </div>
          </div>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard
            label="HRV"
            value={fmt(today.hrv, 0)}
            unit="ms"
            accent="recovery"
            delta={delta(today.hrv, yesterday?.hrv, "ms")}
            hint="vs yesterday"
          />
          <MetricCard
            label="Resting HR"
            value={fmt(today.rhr, 0)}
            unit="bpm"
            accent="alert"
            delta={delta(today.rhr, yesterday?.rhr, "bpm")}
            hint="vs yesterday"
          />
          <MetricCard
            label="Sleep"
            value={fmt(today.sleep_hours)}
            unit="hr"
            accent="sleep"
            delta={delta(today.sleep_hours, yesterday?.sleep_hours, "h")}
            hint={today.sleep_score != null ? `score ${today.sleep_score}` : undefined}
          />
          <MetricCard
            label="Steps"
            value={fmtInt(today.steps)}
            delta={delta(today.steps, yesterday?.steps)}
            hint="vs yesterday"
          />
          <MetricCard
            label="Weight"
            value={fmt(latestInBody.weight_lbs)}
            unit="lbs"
            hint={`scan ${latestInBody.date.slice(5)}`}
          />
          <MetricCard
            label="Body Fat"
            value={fmt(latestInBody.bf_pct)}
            unit="%"
            accent="warn"
            hint={`SMM ${fmt(latestInBody.skeletal_muscle_lbs)} lbs`}
          />
        </div>
      </section>

      {/* 7-day mini-trends */}
      <section className="grid gap-4 lg:grid-cols-3">
        <Card title="HRV — 7d" hint={`${last7[0].date.slice(5)} → today`}>
          <TrendArea data={last7} dataKey="hrv" color="var(--color-recovery)" unit="ms" height={140} />
        </Card>
        <Card title="Sleep — 7d" hint="hours">
          <TrendArea data={last7} dataKey="sleep_hours" color="var(--color-sleep)" unit="h" height={140} />
        </Card>
        <Card title="Steps — 7d">
          <BarSeries data={last7} dataKey="steps" color="var(--color-strain)" height={140} />
        </Card>
      </section>

      {/* Last night sleep breakdown */}
      <section className="grid gap-4 lg:grid-cols-[1fr_2fr]">
        <Card title="Last Night" hint={sleep[sleep.length - 1].date.slice(5)}>
          <SleepBreakdown s={sleep[sleep.length - 1]} />
        </Card>
        <Card title="Sleep Stages — 7d">
          <SleepStages data={sleep} />
        </Card>
      </section>
    </div>
  );
}

function SleepBreakdown({ s }: { s: ReturnType<typeof mockSleep>[number] }) {
  const total = s.deep_min + s.rem_min + s.light_min;
  const rows = [
    { label: "Deep", min: s.deep_min, color: "var(--color-sleep)" },
    { label: "REM", min: s.rem_min, color: "var(--color-strain)" },
    { label: "Light", min: s.light_min, color: "var(--color-recovery)" },
    { label: "Awake", min: s.awake_min, color: "var(--color-text-faint)" },
  ];
  return (
    <div className="space-y-3">
      <div>
        <div className="metric-num text-3xl font-semibold">
          {Math.floor(total / 60)}h {total % 60}m
        </div>
        <div className="text-xs text-[var(--color-text-faint)]">
          {s.efficiency}% efficiency
        </div>
      </div>
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-3 text-sm">
            <span className="w-12 text-[var(--color-text-dim)]">{r.label}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-border)]">
              <div
                className="h-full rounded-full"
                style={{ width: `${(r.min / (total + s.awake_min)) * 100}%`, background: r.color }}
              />
            </div>
            <span className="metric-num w-14 text-right text-xs text-[var(--color-text-dim)]">
              {Math.floor(r.min / 60)}h {r.min % 60}m
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

import { StackedBars } from "@/components/charts";

function SleepStages({ data }: { data: ReturnType<typeof mockSleep> }) {
  return (
    <StackedBars
      data={data}
      keys={[
        { key: "deep_min", color: "var(--color-sleep)", label: "Deep" },
        { key: "rem_min", color: "var(--color-strain)", label: "REM" },
        { key: "light_min", color: "var(--color-recovery)", label: "Light" },
        { key: "awake_min", color: "#3a3a3a", label: "Awake" },
      ]}
      height={200}
    />
  );
}
