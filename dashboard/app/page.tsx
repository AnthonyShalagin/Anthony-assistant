import { Card, MetricCard } from "@/components/card";
import { TrendArea, BarSeries } from "@/components/charts";
import { RecoveryRing } from "@/components/recovery-ring";
import { getDailyMetrics, getInBodyScans, getSleepDetails } from "@/lib/mock";

export default function TodayPage() {
  const days = getDailyMetrics(30);
  const today = days[days.length - 1];
  const yesterday = days[days.length - 2];
  const sleep = getSleepDetails(7);
  const inbody = getInBodyScans();
  const latestInBody = inbody[inbody.length - 1];

  const delta = (a: number, b: number, unit = "") => {
    const d = a - b;
    return { value: `${d >= 0 ? "+" : ""}${d.toFixed(unit === "%" ? 1 : 0)}${unit}`, positive: d >= 0 };
  };

  const last7 = days.slice(-7);

  return (
    <div className="space-y-8">
      {/* Hero: Recovery + summary */}
      <section className="grid gap-6 lg:grid-cols-[auto_1fr]">
        <Card className="flex flex-col items-center justify-center bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-surface-2)]">
          <RecoveryRing value={today.recovery_score} />
          <div className="mt-4 text-center">
            <div className="text-xs uppercase tracking-[0.25em] text-[var(--color-text-faint)]">
              Strain
            </div>
            <div className="metric-num mt-1 text-2xl font-semibold text-[var(--color-strain)]">
              {today.strain.toFixed(1)}
            </div>
          </div>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard
            label="HRV"
            value={today.hrv}
            unit="ms"
            accent="recovery"
            delta={delta(today.hrv, yesterday.hrv, "ms")}
            hint="vs yesterday"
          />
          <MetricCard
            label="Resting HR"
            value={today.rhr}
            unit="bpm"
            accent="alert"
            delta={delta(today.rhr, yesterday.rhr, "bpm")}
            hint="vs yesterday"
          />
          <MetricCard
            label="Sleep"
            value={today.sleep_hours.toFixed(1)}
            unit="hr"
            accent="sleep"
            delta={delta(today.sleep_hours, yesterday.sleep_hours, "h")}
            hint={`score ${today.sleep_score}`}
          />
          <MetricCard
            label="Steps"
            value={today.steps.toLocaleString()}
            delta={delta(today.steps, yesterday.steps)}
            hint="vs yesterday"
          />
          <MetricCard
            label="Weight"
            value={latestInBody.weight_lbs.toFixed(1)}
            unit="lbs"
            hint={`scan ${latestInBody.date.slice(5)}`}
          />
          <MetricCard
            label="Body Fat"
            value={latestInBody.bf_pct.toFixed(1)}
            unit="%"
            accent="warn"
            hint={`SMM ${latestInBody.skeletal_muscle_lbs.toFixed(1)} lbs`}
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

function SleepBreakdown({ s }: { s: ReturnType<typeof getSleepDetails>[number] }) {
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

function SleepStages({ data }: { data: ReturnType<typeof getSleepDetails> }) {
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
