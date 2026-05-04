import { Card } from "@/components/card";
import { GOALS, getDailyMetrics, getInBodyScans } from "@/lib/mock";
import { format, parseISO, startOfWeek } from "date-fns";

export default function GoalsPage() {
  const metrics = getDailyMetrics(90);
  const inbody = getInBodyScans();

  // Compute weekly aggregates
  const weekly = aggregateWeekly(metrics);
  // Latest week
  const latestWeek = weekly[weekly.length - 1];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Goals</h1>
        <p className="mt-1 text-xs text-[var(--color-text-faint)]">
          Weekly average for steps & sleep · Monthly target for body fat.
        </p>
      </div>

      <section className="grid gap-4 lg:grid-cols-3">
        {GOALS.map((g) => {
          if (g.metric === "steps") {
            const current = latestWeek.steps_avg;
            const pct = Math.min(100, (current / g.target) * 100);
            const hit = current >= g.target;
            return <GoalCard key={g.metric} title={g.label} period={g.period} current={Math.round(current).toLocaleString()} target={g.target.toLocaleString()} unit={g.unit} pct={pct} hit={hit} />;
          }
          if (g.metric === "sleep") {
            const current = latestWeek.sleep_avg;
            const pct = Math.min(100, (current / g.target) * 100);
            const hit = current >= g.target;
            return <GoalCard key={g.metric} title={g.label} period={g.period} current={current.toFixed(1)} target={g.target.toFixed(1)} unit={g.unit} pct={pct} hit={hit} />;
          }
          // body fat — lower is better
          const latest = inbody[inbody.length - 1].bf_pct;
          const pct = Math.min(100, (g.target / latest) * 100);
          const hit = latest <= g.target;
          return <GoalCard key={g.metric} title={g.label} period={g.period} current={latest.toFixed(1)} target={g.target.toFixed(1)} unit={g.unit} pct={pct} hit={hit} />;
        })}
      </section>

      <Card title="Weekly History" hint="last 12 weeks">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-faint)]">
              <th className="py-2">Week of</th>
              <th className="py-2 text-right">Steps avg</th>
              <th className="py-2 text-right">Sleep avg</th>
              <th className="py-2 text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            {weekly.slice(-12).reverse().map((w) => {
              const stepsHit = w.steps_avg >= 8000;
              const sleepHit = w.sleep_avg >= 7.5;
              return (
                <tr key={w.week} className="border-b border-[var(--color-border)]/50">
                  <td className="py-2 text-[var(--color-text-dim)]">{w.week}</td>
                  <td className="py-2 text-right tabular-nums">{Math.round(w.steps_avg).toLocaleString()}</td>
                  <td className="py-2 text-right tabular-nums">{w.sleep_avg.toFixed(1)}</td>
                  <td className="py-2 text-right text-xs">
                    <span className={stepsHit ? "text-[var(--color-recovery)]" : "text-[var(--color-text-faint)]"}>
                      {stepsHit ? "✓" : "—"} steps
                    </span>
                    <span className="mx-1 text-[var(--color-text-faint)]">·</span>
                    <span className={sleepHit ? "text-[var(--color-recovery)]" : "text-[var(--color-text-faint)]"}>
                      {sleepHit ? "✓" : "—"} sleep
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <Card title="Body Fat — Monthly" hint="target 15%">
        <BFHistory inbody={inbody} target={15} />
      </Card>
    </div>
  );
}

function GoalCard({
  title,
  period,
  current,
  target,
  unit,
  pct,
  hit,
}: {
  title: string;
  period: "weekly" | "monthly";
  current: string;
  target: string;
  unit: string;
  pct: number;
  hit: boolean;
}) {
  const color = hit ? "var(--color-recovery)" : "var(--color-warn)";
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
          {title}
        </h3>
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-faint)]">
          {period}
        </span>
      </div>
      <div className="mt-4 flex items-baseline gap-2">
        <span className="metric-num text-4xl font-semibold" style={{ color }}>
          {current}
        </span>
        <span className="text-sm text-[var(--color-text-faint)]">/ {target} {unit}</span>
      </div>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[var(--color-border)]">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="mt-2 text-xs" style={{ color: hit ? "var(--color-recovery)" : "var(--color-text-faint)" }}>
        {hit ? "✓ On track" : "Below target"}
      </div>
    </div>
  );
}

function aggregateWeekly(metrics: ReturnType<typeof getDailyMetrics>) {
  const byWeek = new Map<string, { steps: number[]; sleep: number[] }>();
  for (const m of metrics) {
    const wk = format(startOfWeek(parseISO(m.date), { weekStartsOn: 1 }), "yyyy-MM-dd");
    const acc = byWeek.get(wk) ?? { steps: [], sleep: [] };
    acc.steps.push(m.steps);
    acc.sleep.push(m.sleep_hours);
    byWeek.set(wk, acc);
  }
  return [...byWeek.entries()]
    .map(([week, v]) => ({
      week,
      steps_avg: v.steps.reduce((a, b) => a + b, 0) / v.steps.length,
      sleep_avg: v.sleep.reduce((a, b) => a + b, 0) / v.sleep.length,
    }))
    .sort((a, b) => a.week.localeCompare(b.week));
}

function BFHistory({ inbody, target }: { inbody: ReturnType<typeof getInBodyScans>; target: number }) {
  return (
    <div className="space-y-2">
      {inbody.map((s, idx) => {
        const prev = inbody[idx - 1];
        const delta = prev ? s.bf_pct - prev.bf_pct : null;
        const hit = s.bf_pct <= target;
        return (
          <div key={s.date} className="flex items-center gap-4 border-b border-[var(--color-border)]/50 py-2 text-sm last:border-b-0">
            <span className="w-24 text-[var(--color-text-dim)]">{s.date}</span>
            <span className="metric-num w-16 tabular-nums" style={{ color: hit ? "var(--color-recovery)" : "var(--color-warn)" }}>
              {s.bf_pct.toFixed(1)}%
            </span>
            <div className="flex-1">
              <div className="relative h-1.5 rounded-full bg-[var(--color-border)]">
                <div
                  className="absolute top-0 h-full rounded-full"
                  style={{
                    width: `${Math.min(100, (s.bf_pct / 25) * 100)}%`,
                    background: hit ? "var(--color-recovery)" : "var(--color-warn)",
                  }}
                />
                <div
                  className="absolute -top-0.5 h-2.5 w-0.5"
                  style={{
                    left: `${(target / 25) * 100}%`,
                    background: "var(--color-text)",
                  }}
                  title={`Target ${target}%`}
                />
              </div>
            </div>
            {delta != null && (
              <span className="metric-num w-16 text-right text-xs tabular-nums" style={{ color: delta < 0 ? "var(--color-recovery)" : "var(--color-alert)" }}>
                {delta > 0 ? "+" : ""}{delta.toFixed(1)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
