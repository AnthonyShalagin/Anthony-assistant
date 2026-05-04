"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/card";
import type { StrongSet } from "@/lib/mock";
import { differenceInDays, format, parseISO, startOfWeek } from "date-fns";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const AXIS = "#6b6b6b";
const GRID = "#262626";
const tooltipStyle = {
  background: "#141414",
  border: "1px solid #262626",
  borderRadius: 8,
  fontSize: 12,
  color: "#f5f5f5",
};

const PRIORITY_COLORS = [
  "var(--color-recovery)",
  "var(--color-strain)",
  "var(--color-sleep)",
  "var(--color-warn)",
  "var(--color-alert)",
  "#a1a1a1",
  "#7dd3fc",
  "#fb7185",
];

// Skip cardio + carry-style movements when computing strength PRs / priority lifts
const NON_STRENGTH = new Set([
  "Treadmill",
  "Stairmaster",
  "Running",
  "Cycling",
  "Rowing Machine",
  "Elliptical",
  "Walk",
  "Stretching",
]);

export function StrengthClient({ sets }: { sets: StrongSet[] }) {
  const today = useMemo(() => {
    if (sets.length === 0) return new Date();
    return parseISO(sets.reduce((m, s) => (s.date > m ? s.date : m), sets[0].date));
  }, [sets]);

  // ---------- Priority score per exercise ----------
  // Recency-weighted: a set in the last 4 weeks counts 4x, last 12 weeks 2x,
  // last 26 weeks 1x, anything older 0.3x. Higher = more relevant.
  const priorityScore = useMemo(() => {
    const score = new Map<string, number>();
    for (const s of sets) {
      if (NON_STRENGTH.has(s.exercise)) continue;
      const days = differenceInDays(today, parseISO(s.date));
      let w: number;
      if (days <= 28) w = 4;
      else if (days <= 84) w = 2;
      else if (days <= 182) w = 1;
      else w = 0.3;
      score.set(s.exercise, (score.get(s.exercise) ?? 0) + w);
    }
    return score;
  }, [sets, today]);

  const orderedExercises = useMemo(() => {
    return [...priorityScore.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([name]) => name);
  }, [priorityScore]);

  const topLifts = useMemo(() => orderedExercises.slice(0, 6), [orderedExercises]);

  const [exercise, setExercise] = useState(orderedExercises[0] ?? "Bench Press");

  // Map exercise -> sorted history of {date, top weight, top e1rm, sets, last_seen}
  const historyByExercise = useMemo(() => {
    const m = new Map<
      string,
      { date: string; top_weight: number; top_e1rm: number; sets: number }[]
    >();
    const tmp = new Map<string, Map<string, { w: number; r: number; e1rm: number; sets: number }>>();

    for (const s of sets) {
      const ex = s.exercise;
      if (!tmp.has(ex)) tmp.set(ex, new Map());
      const day = tmp.get(ex)!;
      const cur = day.get(s.date) ?? { w: 0, r: 0, e1rm: 0, sets: 0 };
      cur.sets += 1;
      if (s.weight_lbs > cur.w) cur.w = s.weight_lbs;
      if (s.e1rm > cur.e1rm) cur.e1rm = s.e1rm;
      day.set(s.date, cur);
    }

    for (const [ex, day] of tmp.entries()) {
      const arr = [...day.entries()]
        .map(([date, v]) => ({
          date,
          top_weight: v.w,
          top_e1rm: v.e1rm,
          sets: v.sets,
        }))
        .sort((a, b) => a.date.localeCompare(b.date));
      m.set(ex, arr);
    }
    return m;
  }, [sets]);

  // ---------- Per-exercise selected progress ----------
  const exerciseProgress = useMemo(() => {
    return historyByExercise.get(exercise) ?? [];
  }, [historyByExercise, exercise]);

  // ---------- Top 4 e1RM trend (the user's actual most-relevant lifts) ----------
  const e1rmTrend = useMemo(() => {
    const tracked = topLifts.slice(0, 4);
    const byDate = new Map<string, Record<string, number>>();
    for (const s of sets) {
      if (!tracked.includes(s.exercise)) continue;
      const row = byDate.get(s.date) ?? {};
      if ((row[s.exercise] ?? 0) < s.e1rm) row[s.exercise] = s.e1rm;
      byDate.set(s.date, row);
    }
    return [...byDate.entries()]
      .map(([date, vals]) => ({ date, ...vals }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [sets, topLifts]);

  // ---------- Weekly volume by muscle group ----------
  const weeklyVolume = useMemo(() => {
    const byWeek = new Map<string, Record<string, number>>();
    for (const s of sets) {
      const wk = format(startOfWeek(parseISO(s.date), { weekStartsOn: 1 }), "yyyy-MM-dd");
      const row = byWeek.get(wk) ?? {};
      const vol = s.weight_lbs * s.reps;
      row[s.muscle_group] = (row[s.muscle_group] ?? 0) + vol;
      byWeek.set(wk, row);
    }
    return [...byWeek.entries()]
      .map(([date, vals]) => ({ date, ...vals }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [sets]);

  return (
    <div className="space-y-8">
      {/* ============= PRIORITY LIFTS ============= */}
      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--color-text-dim)]">
            Priority Lifts
          </h2>
          <span className="text-[10px] text-[var(--color-text-faint)]">
            ranked by recent frequency · last 6 months weighted heavier
          </span>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {topLifts.map((name, i) => (
            <PriorityLiftCard
              key={name}
              name={name}
              history={historyByExercise.get(name) ?? []}
              today={today}
              color={PRIORITY_COLORS[i % PRIORITY_COLORS.length]}
              onSelect={() => setExercise(name)}
            />
          ))}
        </div>
      </section>

      {/* ============= e1RM TREND ============= */}
      <Card
        title="Estimated 1RM — Top Lifts"
        hint="Epley formula · top 4 by recency"
      >
        <E1RMChart data={e1rmTrend} lifts={topLifts.slice(0, 4)} />
      </Card>

      {/* ============= PER-EXERCISE PROGRESS ============= */}
      <Card title="Per-Exercise Progress" hint="Top set per workout">
        <div className="mb-4 flex flex-wrap gap-1">
          {orderedExercises.map((e) => (
            <button
              key={e}
              onClick={() => setExercise(e)}
              className={`rounded px-2.5 py-1 text-xs transition-colors ${
                e === exercise
                  ? "bg-[var(--color-strain)] text-black"
                  : "bg-[var(--color-surface-2)] text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
              }`}
            >
              {e}
            </button>
          ))}
        </div>
        {exerciseProgress.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart
              data={exerciseProgress}
              margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
            >
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis
                dataKey="date"
                stroke={AXIS}
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: string) => v.slice(2, 7)}
                minTickGap={24}
              />
              <YAxis stroke={AXIS} fontSize={10} tickLine={false} axisLine={false} width={36} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: GRID }} />
              <Line
                type="monotone"
                dataKey="top_weight"
                name="Top weight"
                stroke="var(--color-strain)"
                strokeWidth={2}
                dot={{ r: 2 }}
              />
              <Line
                type="monotone"
                dataKey="top_e1rm"
                name="e1RM"
                stroke="var(--color-recovery)"
                strokeWidth={2}
                strokeDasharray="3 3"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-[var(--color-text-faint)]">No data.</p>
        )}
      </Card>

      {/* ============= WEEKLY VOLUME ============= */}
      <Card title="Weekly Volume" hint="weight × reps · stacked by muscle group">
        <VolumeChart data={weeklyVolume} />
      </Card>
    </div>
  );
}

// ---------- Priority Lift Card ----------

function PriorityLiftCard({
  name,
  history,
  today,
  color,
  onSelect,
}: {
  name: string;
  history: { date: string; top_weight: number; top_e1rm: number; sets: number }[];
  today: Date;
  color: string;
  onSelect: () => void;
}) {
  if (history.length === 0) return null;
  const latest = history[history.length - 1];
  const earliest = history[0];

  // Trend: latest weight vs 90 days ago (or earliest if shorter)
  const cutoffDate = format(
    new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000),
    "yyyy-MM-dd"
  );
  const baseline = (() => {
    const before = history.filter((h) => h.date <= cutoffDate);
    if (before.length === 0) return earliest;
    return before[before.length - 1];
  })();
  const delta = latest.top_e1rm - baseline.top_e1rm;
  const deltaPct = baseline.top_e1rm > 0 ? (delta / baseline.top_e1rm) * 100 : 0;

  const daysSince = differenceInDays(today, parseISO(latest.date));
  const last90 = history.filter(
    (h) => differenceInDays(today, parseISO(h.date)) <= 90
  );

  return (
    <button
      onClick={onSelect}
      className="group rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 text-left transition-colors hover:bg-[var(--color-surface-2)]"
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate text-sm font-medium text-[var(--color-text)]">
          {name}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-faint)]">
          {last90.length} sessions · 90d
        </span>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="metric-num text-3xl font-semibold" style={{ color }}>
          {Math.round(latest.top_weight)}
        </span>
        <span className="text-xs text-[var(--color-text-faint)]">
          lbs · top set
        </span>
      </div>
      <div className="mt-1 flex items-center gap-2 text-xs">
        <span className="text-[var(--color-text-dim)]">
          e1RM <span className="metric-num text-[var(--color-text)]">{Math.round(latest.top_e1rm)}</span>
        </span>
        {history.length >= 2 && (
          <span
            className={
              delta > 0
                ? "text-[var(--color-recovery)]"
                : delta < 0
                ? "text-[var(--color-alert)]"
                : "text-[var(--color-text-faint)]"
            }
          >
            {delta > 0 ? "▲" : delta < 0 ? "▼" : "—"} {Math.abs(deltaPct).toFixed(1)}%
          </span>
        )}
        <span className="text-[var(--color-text-faint)]">
          · {daysSince === 0 ? "today" : `${daysSince}d ago`}
        </span>
      </div>

      {history.length >= 2 && (
        <div className="mt-3 -mx-1 h-14">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={history}
              margin={{ top: 4, right: 4, left: 4, bottom: 0 }}
            >
              <defs>
                <linearGradient
                  id={`pri-${name.replace(/\W/g, "")}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={color} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" hide />
              <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
              <Area
                type="monotone"
                dataKey="top_e1rm"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#pri-${name.replace(/\W/g, "")})`}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </button>
  );
}

// ---------- Charts ----------

function E1RMChart({
  data,
  lifts,
}: {
  data: Record<string, number | string>[];
  lifts: string[];
}) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="date"
          stroke={AXIS}
          fontSize={10}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: string) => v.slice(2, 7)}
          minTickGap={24}
        />
        <YAxis stroke={AXIS} fontSize={10} tickLine={false} axisLine={false} width={36} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: GRID }} />
        <Legend wrapperStyle={{ fontSize: 11, color: "#a1a1a1" }} iconType="line" />
        {lifts.map((lift, i) => (
          <Line
            key={lift}
            type="monotone"
            dataKey={lift}
            stroke={PRIORITY_COLORS[i % PRIORITY_COLORS.length]}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function VolumeChart({ data }: { data: Record<string, number | string>[] }) {
  const groups = ["Legs", "Back", "Chest", "Shoulders", "Arms", "Core"];
  const colors: Record<string, string> = {
    Legs: "var(--color-recovery)",
    Back: "var(--color-strain)",
    Chest: "var(--color-sleep)",
    Shoulders: "var(--color-warn)",
    Arms: "var(--color-alert)",
    Core: "#a1a1a1",
  };
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="date"
          stroke={AXIS}
          fontSize={10}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: string) => v.slice(2, 7)}
        />
        <YAxis stroke={AXIS} fontSize={10} tickLine={false} axisLine={false} width={48} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1c1c1c" }} />
        <Legend wrapperStyle={{ fontSize: 11, color: "#a1a1a1" }} iconType="square" />
        {groups.map((g) => (
          <Bar key={g} dataKey={g} stackId="vol" fill={colors[g]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
