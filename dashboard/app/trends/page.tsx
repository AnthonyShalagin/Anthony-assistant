import { Card } from "@/components/card";
import { TrendArea, TrendLine, BarSeries } from "@/components/charts";
import { getDailyMetrics } from "@/lib/mock";

export default function TrendsPage() {
  const data = getDailyMetrics(90);
  const last30 = data.slice(-30);

  const avg = (arr: number[]) =>
    Math.round((arr.reduce((a, b) => a + b, 0) / arr.length) * 10) / 10;

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Trends</h1>
        <div className="flex gap-1 text-xs">
          {["7d", "30d", "90d"].map((p) => (
            <span
              key={p}
              className="rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1 text-[var(--color-text-dim)]"
            >
              {p}
            </span>
          ))}
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card title="HRV (ms)" hint={`30d avg ${avg(last30.map((d) => d.hrv))} ms`}>
          <TrendArea data={last30} dataKey="hrv" color="var(--color-recovery)" unit="ms" height={220} />
        </Card>
        <Card title="Resting HR (bpm)" hint={`30d avg ${avg(last30.map((d) => d.rhr))} bpm`}>
          <TrendLine data={last30} dataKey="rhr" color="var(--color-alert)" unit="bpm" height={220} />
        </Card>
        <Card title="Sleep (hours)" hint={`30d avg ${avg(last30.map((d) => d.sleep_hours))} h`}>
          <TrendArea data={last30} dataKey="sleep_hours" color="var(--color-sleep)" unit="h" height={220} />
        </Card>
        <Card title="Sleep Score" hint={`30d avg ${avg(last30.map((d) => d.sleep_score))}`}>
          <TrendLine data={last30} dataKey="sleep_score" color="var(--color-sleep)" height={220} />
        </Card>
        <Card title="Steps" hint={`30d avg ${Math.round(avg(last30.map((d) => d.steps))).toLocaleString()}`}>
          <BarSeries data={last30} dataKey="steps" color="var(--color-strain)" height={220} />
        </Card>
        <Card title="Recovery Score" hint={`30d avg ${avg(last30.map((d) => d.recovery_score))}`}>
          <TrendArea data={last30} dataKey="recovery_score" color="var(--color-recovery)" height={220} />
        </Card>
      </section>
    </div>
  );
}
