"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/card";
import { TrendChart } from "@/components/charts";
import { cn } from "@/lib/cn";
import { STATUS_VAR, daysBetween, shortDate, todayISO, weekStart, type Status } from "@/lib/health";
import type { StrongSet } from "@/lib/mock";

const LIFTS_PER_WEEK = 2;
const WEEKS = 12;
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Cardio and stretching aren't strength lifts
const NON_STRENGTH = new Set(["Treadmill", "Stairmaster", "Running", "Cycling", "Rowing Machine", "Elliptical", "Walk", "Stretching", "Warm Up"]);

type Session = { date: string; exercises: number; sets: number };
type LiftDay = { date: string; e1rm: number; topWeight: number; topReps: number };

export function StrengthClient({ sets }: { sets: StrongSet[] }) {
  const today = todayISO();
  const [selected, setSelected] = useState<string | null>(null);

  const sessions = useMemo<Session[]>(() => {
    const byDate = new Map<string, { ex: Set<string>; sets: number }>();
    for (const s of sets) {
      const d = byDate.get(s.date) ?? { ex: new Set(), sets: 0 };
      d.ex.add(s.exercise);
      d.sets += 1;
      byDate.set(s.date, d);
    }
    return [...byDate.entries()]
      .map(([date, v]) => ({ date, exercises: v.ex.size, sets: v.sets }))
      .sort((a, b) => b.date.localeCompare(a.date));
  }, [sets]);

  // Lifts per week for the last 12 weeks, oldest first
  const weeks = useMemo(() => {
    const thisWeek = weekStart(today);
    return Array.from({ length: WEEKS }, (_, i) => {
      const d = new Date(thisWeek + "T12:00:00");
      d.setDate(d.getDate() - (WEEKS - 1 - i) * 7);
      const start = d.toISOString().slice(0, 10);
      return { start, count: sessions.filter((s) => weekStart(s.date) === start).length };
    });
  }, [sessions, today]);
  const thisWeek = weeks[weeks.length - 1].count;
  const hitWeeks = weeks.slice(0, -1).slice(-4).filter((w) => w.count >= LIFTS_PER_WEEK).length;

  // Per-lift history: best estimated 1RM (or top reps for bodyweight) each session
  const lifts = useMemo(() => {
    const score = new Map<string, number>();
    const days = new Map<string, Map<string, LiftDay>>();
    for (const s of sets) {
      if (NON_STRENGTH.has(s.exercise)) continue;
      const age = daysBetween(s.date, today);
      score.set(s.exercise, (score.get(s.exercise) ?? 0) + (age <= 28 ? 4 : age <= 84 ? 2 : 1));
      const byDate = days.get(s.exercise) ?? new Map<string, LiftDay>();
      const cur = byDate.get(s.date) ?? { date: s.date, e1rm: 0, topWeight: 0, topReps: 0 };
      cur.e1rm = Math.max(cur.e1rm, s.e1rm || 0);
      cur.topWeight = Math.max(cur.topWeight, s.weight_lbs || 0);
      cur.topReps = Math.max(cur.topReps, s.reps || 0);
      byDate.set(s.date, cur);
      days.set(s.exercise, byDate);
    }
    return [...score.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map(([name]) => {
        const history = [...days.get(name)!.values()].sort((a, b) => a.date.localeCompare(b.date));
        const bodyweight = history.every((h) => h.topWeight === 0);
        const metric = (h: LiftDay) => (bodyweight ? h.topReps : h.e1rm);
        const latest = history[history.length - 1];
        const past = history.filter((h) => daysBetween(h.date, latest.date) >= 80);
        const base = past.length ? metric(past[past.length - 1]) : null;
        const change = base ? ((metric(latest) - base) / base) * 100 : null;
        return { name, history, bodyweight, latest, change, metric };
      });
  }, [sets, today]);

  const active = lifts.find((l) => l.name === (selected ?? lifts[0]?.name));
  const last = sessions[0];

  if (sessions.length === 0) {
    return (
      <div className="mx-auto max-w-3xl">
        <h1 className="text-[28px] font-semibold sm:text-[34px]">Training</h1>
        <p className="mt-2 text-[15px] text-[var(--color-text-dim)]">No Hevy sessions in the last few months.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.02em] sm:text-[34px]">
          {thisWeek >= LIFTS_PER_WEEK
            ? `${thisWeek} lifts this week. Goal met.`
            : `${thisWeek} of ${LIFTS_PER_WEEK} lifts this week`}
        </h1>
        <p className="mt-1 text-[15px] text-[var(--color-text-dim)]">
          Hit the goal {hitWeeks} of the last 4 weeks · last lift {shortDate(last.date)}
          {daysBetween(last.date, today) >= 4 && (
            <span style={{ color: STATUS_VAR.watch }}> ({daysBetween(last.date, today)} days ago)</span>
          )}
        </p>
      </header>

      <Card title="Lifts per week" hint={`Goal ${LIFTS_PER_WEEK}`}>
        <div className="relative flex h-28 items-end gap-1.5 sm:gap-2">
          <div
            className="pointer-events-none absolute inset-x-0 border-t border-dashed"
            style={{ bottom: `${(LIFTS_PER_WEEK / 4) * 100}%`, borderColor: "var(--color-good)" }}
            aria-hidden
          />
          {weeks.map((w, i) => (
            <div key={w.start} className="flex h-full flex-1 flex-col items-center justify-end" title={`Week of ${shortDate(w.start)}: ${w.count} lifts`}>
              <div
                className={cn("w-full max-w-7 rounded-md", i === weeks.length - 1 && "opacity-60")}
                style={{
                  height: `${(Math.min(w.count, 4) / 4) * 100}%`,
                  minHeight: w.count ? 6 : 2,
                  background: w.count >= LIFTS_PER_WEEK ? "var(--color-good)" : w.count ? "var(--color-chart)" : "var(--color-surface-2)",
                }}
              />
            </div>
          ))}
        </div>
        <div className="mt-2 flex justify-between text-[11px] text-[var(--color-text-dim)]">
          <span>{shortDate(weeks[0].start)}</span>
          <span>This week</span>
        </div>
      </Card>

      <Card title="Recent sessions">
        <ul className="divide-y divide-[var(--color-border)]">
          {sessions.slice(0, 5).map((s) => {
            const d = new Date(s.date + "T12:00:00");
            return (
              <li key={s.date} className="flex items-baseline justify-between gap-3 py-2.5 text-[15px] first:pt-0 last:pb-0">
                <span>
                  {WEEKDAYS[d.getDay()]}, {shortDate(s.date)}
                </span>
                <span className="text-[13px] text-[var(--color-text-dim)]">
                  {s.exercises} exercises · {s.sets} sets
                </span>
              </li>
            );
          })}
        </ul>
      </Card>

      <section>
        <h2 className="text-[17px] font-semibold">Main lifts</h2>
        <p className="mt-1 text-[13px] text-[var(--color-text-dim)]">
          Estimated 1-rep max: the most you could lift once, worked out from your sets. Change is over the last 3
          months. Select a lift to see its history.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {lifts.map((l) => {
            const status: Status = l.change == null ? "none" : l.change >= 1 ? "good" : l.change <= -5 ? "bad" : "watch";
            const isActive = active?.name === l.name;
            return (
              <button
                key={l.name}
                onClick={() => setSelected(l.name)}
                aria-pressed={isActive}
                className={cn(
                  "rounded-2xl border bg-[var(--color-surface)] p-3 text-left transition-colors sm:p-4",
                  isActive ? "border-[var(--color-text)]" : "border-[var(--color-border)] hover:bg-[var(--color-surface-2)]"
                )}
              >
                <div className="truncate text-[13px] text-[var(--color-text-dim)]">{l.name}</div>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="metric-num text-[26px] font-semibold leading-none">
                    {Math.round(l.metric(l.latest))}
                  </span>
                  <span className="text-[13px] text-[var(--color-text-dim)]">{l.bodyweight ? "reps" : "lb"}</span>
                </div>
                <div className="mt-2 text-[13px] font-medium" style={{ color: STATUS_VAR[status] }}>
                  {l.change == null ? "New lift" : `${l.change > 0 ? "+" : ""}${l.change.toFixed(0)}% in 3 months`}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {active && active.history.length > 1 && (
        <Card title={active.name} hint={active.bodyweight ? "Top set, reps" : "Estimated 1-rep max, lb"}>
          <TrendChart
            points={active.history.map((h) => ({ date: h.date, value: active.metric(h) || null }))}
            unit={active.bodyweight ? "reps" : "lb"}
          />
        </Card>
      )}
    </div>
  );
}
