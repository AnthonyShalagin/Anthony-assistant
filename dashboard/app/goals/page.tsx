import { fetchBloodwork, fetchDailyMetrics, fetchStrongSets } from "@/lib/data";
import { getDef } from "@/lib/biomarker-info";
import { STATUS_VAR, avg, shortDate, todayISO, weekStart, withCanonical, type Status } from "@/lib/health";

export const dynamic = "force-dynamic";

// Anthony's plan: lift 2x a week, ApoB down, sleep, steps.
const LIFTS = 2;
const SLEEP = 7.5;
const STEPS = 8000;
const WEEKS = 12;

const roundTo = (v: number | null, d: number) => (v == null ? null : Number(v.toFixed(d)));

type Week = { start: string; lifts: number; sleep: number | null; steps: number | null };

export default async function GoalsPage() {
  const [metrics, sets, markers] = await Promise.all([
    fetchDailyMetrics(WEEKS * 7 + 7),
    fetchStrongSets(WEEKS + 1),
    fetchBloodwork(),
  ]);

  // Last 12 weeks, oldest first; the final one is this (unfinished) week
  const thisWeek = weekStart(todayISO());
  const starts: string[] = [];
  for (let i = WEEKS - 1; i >= 0; i--) {
    const d = new Date(thisWeek + "T12:00:00");
    d.setDate(d.getDate() - i * 7);
    starts.push(d.toISOString().slice(0, 10));
  }
  const sessionDates = [...new Set(sets.map((s) => s.date))];
  const weeks: Week[] = starts.map((start) => {
    const days = metrics.filter((m) => weekStart(m.date) === start);
    return {
      start,
      lifts: sessionDates.filter((d) => weekStart(d) === start).length,
      sleep: roundTo(avg(days.map((d) => d.sleep_hours)), 1),
      steps: avg(days.map((d) => d.steps)),
    };
  });
  const current = weeks[weeks.length - 1];
  const done = weeks.slice(0, -1);
  const last4 = done.slice(-4);

  const apob = markers
    .map(withCanonical)
    .filter((m) => getDef(m.marker)?.display === "Apolipoprotein B")
    .sort((a, b) => a.panel_date.localeCompare(b.panel_date));
  const apobTarget = getDef("ApoB")?.ref_high ?? 90;
  const apobLatest = apob[apob.length - 1];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-[28px] font-semibold tracking-[-0.02em] sm:text-[34px]">Goals</h1>
        <p className="mt-1 text-[15px] text-[var(--color-text-dim)]">
          The four targets in your health plan. Dots show the last {WEEKS} weeks, newest on the right.
        </p>
      </header>

      <Goal
        title="Lift twice a week"
        source="Hevy"
        value={`${current.lifts}`}
        unit={`lift${current.lifts === 1 ? "" : "s"} this week`}
        pct={(current.lifts / LIFTS) * 100}
        status={current.lifts >= LIFTS ? "good" : "watch"}
        summary={`Hit ${last4.filter((w) => w.lifts >= LIFTS).length} of the last 4 weeks.`}
        dots={weeks.map((w, i) => dot(w.lifts >= LIFTS, i === weeks.length - 1, w.start, `${w.lifts} lifts`))}
      />

      <Goal
        title={`Get ApoB under ${apobTarget}`}
        source={apobLatest ? `Labs, ${shortDate(apobLatest.panel_date)}` : "Labs"}
        value={apobLatest ? `${apobLatest.value}` : "–"}
        unit="mg/dL"
        pct={apobLatest ? Math.min(100, (apobTarget / apobLatest.value) * 100) : 0}
        status={!apobLatest ? "none" : apobLatest.value <= apobTarget ? "good" : "bad"}
        summary={
          !apobLatest
            ? "No ApoB result yet."
            : apobLatest.value <= apobTarget
              ? "At goal. ApoB counts the particles that build plaque in arteries."
              : `${Math.round(apobLatest.value - apobTarget)} above goal. ApoB counts the particles that build plaque in arteries.`
        }
        dots={apob.map((m, i) =>
          dot(m.value <= apobTarget, false, m.panel_date, `${m.value} mg/dL`, i === apob.length - 1)
        )}
        dotsLabel="Each result"
      />

      <Goal
        title={`Sleep ${SLEEP} hours a night`}
        source="Oura"
        value={current.sleep != null ? current.sleep.toFixed(1) : "–"}
        unit="h average this week"
        pct={current.sleep != null ? Math.min(100, (current.sleep / SLEEP) * 100) : 0}
        status={current.sleep == null ? "none" : current.sleep >= SLEEP ? "good" : "watch"}
        summary={`Hit ${last4.filter((w) => (w.sleep ?? 0) >= SLEEP).length} of the last 4 weeks.`}
        dots={weeks.map((w, i) =>
          dot((w.sleep ?? 0) >= SLEEP, i === weeks.length - 1, w.start, w.sleep != null ? `${w.sleep.toFixed(1)} h` : "No data")
        )}
      />

      <Goal
        title={`Walk ${STEPS.toLocaleString()} steps a day`}
        source="Oura"
        value={current.steps != null ? Math.round(current.steps).toLocaleString() : "–"}
        unit="average this week"
        pct={current.steps != null ? Math.min(100, (current.steps / STEPS) * 100) : 0}
        status={current.steps == null ? "none" : current.steps >= STEPS ? "good" : "watch"}
        summary={`Hit ${last4.filter((w) => (w.steps ?? 0) >= STEPS).length} of the last 4 weeks.`}
        dots={weeks.map((w, i) =>
          dot((w.steps ?? 0) >= STEPS, i === weeks.length - 1, w.start, w.steps != null ? `${Math.round(w.steps).toLocaleString()} steps` : "No data")
        )}
      />
    </div>
  );
}

type Dot = { hit: boolean; inProgress: boolean; label: string };

function dot(hit: boolean, inProgress: boolean, date: string, detail: string, latest = false): Dot {
  const when = inProgress ? "This week so far" : latest ? `Latest, ${shortDate(date)}` : `Week of ${shortDate(date)}`;
  return { hit, inProgress, label: `${when}: ${detail}${hit ? ", goal met" : ""}` };
}

function Goal({
  title,
  source,
  value,
  unit,
  pct,
  status,
  summary,
  dots,
  dotsLabel = `Last ${WEEKS} weeks`,
}: {
  title: string;
  source: string;
  value: string;
  unit: string;
  pct: number;
  status: Status;
  summary: string;
  dots: Dot[];
  dotsLabel?: string;
}) {
  const color = STATUS_VAR[status];
  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-[17px] font-semibold">{title}</h2>
        <span className="shrink-0 text-[13px] text-[var(--color-text-dim)]">{source}</span>
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="metric-num text-[32px] font-semibold leading-none">{value}</span>
        <span className="text-[15px] text-[var(--color-text-dim)]">{unit}</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
        <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} />
      </div>
      <p className="mt-2 text-[15px]" style={{ color: status === "good" ? color : "var(--color-text-dim)" }}>
        {summary}
      </p>
      {dots.length > 0 && (
        <div className="mt-3">
          <div className="text-[13px] text-[var(--color-text-dim)]">{dotsLabel}</div>
          <div className="mt-1.5 flex flex-wrap gap-1.5" role="list">
            {dots.map((d, i) => (
              <span
                key={i}
                role="listitem"
                title={d.label}
                aria-label={d.label}
                className="h-3.5 w-3.5 rounded-full"
                style={{
                  background: d.hit ? "var(--color-good)" : "var(--color-surface-2)",
                  outline: d.inProgress ? "1.5px dashed var(--color-text-dim)" : undefined,
                  outlineOffset: 2,
                }}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
