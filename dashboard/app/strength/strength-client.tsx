"use client";

import { useMemo, useState } from "react";
import { Card, MetricCard } from "@/components/card";
import { TrendLine, BarSeries } from "@/components/charts";
import type { StrongSet } from "@/lib/mock";
import { format, parseISO, startOfWeek } from "date-fns";

export function StrengthClient({ sets }: { sets: StrongSet[] }) {
  const exercises = useMemo(
    () => Array.from(new Set(sets.map((s) => s.exercise))).sort(),
    [sets]
  );
  const [exercise, setExercise] = useState(exercises[0] ?? "Back Squat");

  // 1) Per-exercise weight over time (top set per workout)
  const exerciseProgress = useMemo(() => {
    const byDate = new Map<string, number>();
    for (const s of sets) {
      if (s.exercise !== exercise) continue;
      const top = byDate.get(s.date) ?? 0;
      if (s.weight_lbs > top) byDate.set(s.date, s.weight_lbs);
    }
    return [...byDate.entries()]
      .map(([date, weight_lbs]) => ({ date, weight_lbs }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [sets, exercise]);

  // 2) Estimated 1RM for big lifts
  const BIG_LIFTS = ["Back Squat", "Bench Press", "Deadlift", "Overhead Press"];
  const e1rmTrend = useMemo(() => {
    // Daily best e1rm per lift, then merge by date
    const byDate = new Map<string, Record<string, number>>();
    for (const s of sets) {
      if (!BIG_LIFTS.includes(s.exercise)) continue;
      const row = byDate.get(s.date) ?? {};
      if ((row[s.exercise] ?? 0) < s.e1rm) row[s.exercise] = s.e1rm;
      byDate.set(s.date, row);
    }
    return [...byDate.entries()]
      .map(([date, vals]) => ({ date, ...vals }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [sets]);

  // 3) Weekly volume per muscle group
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

  // PRs
  const prs = useMemo(() => {
    const byEx = new Map<string, { weight: number; e1rm: number; date: string }>();
    for (const s of sets) {
      const cur = byEx.get(s.exercise);
      if (!cur || s.e1rm > cur.e1rm) {
        byEx.set(s.exercise, { weight: s.weight_lbs, e1rm: s.e1rm, date: s.date });
      }
    }
    return Array.from(byEx.entries())
      .filter(([, v]) => v.weight > 0)
      .sort((a, b) => b[1].e1rm - a[1].e1rm);
  }, [sets]);

  return (
    <div className="space-y-8">
      {/* PR cards */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {prs.slice(0, 4).map(([name, p]) => (
          <MetricCard
            key={name}
            label={name}
            value={p.weight}
            unit="lbs"
            accent="strain"
            hint={`e1RM ${p.e1rm} · ${p.date.slice(5)}`}
          />
        ))}
      </section>

      {/* Per-exercise progress */}
      <Card
        title="Per-Exercise Progress"
        hint="Top set per workout"
      >
        <div className="mb-4 flex flex-wrap gap-1">
          {exercises.map((e) => (
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
          <TrendLine
            data={exerciseProgress}
            dataKey="weight_lbs"
            color="var(--color-strain)"
            unit=" lbs"
            height={240}
          />
        ) : (
          <p className="text-sm text-[var(--color-text-faint)]">No data.</p>
        )}
      </Card>

      {/* e1RM big lifts */}
      <Card title="Estimated 1RM — Big Lifts" hint="Epley formula">
        <E1RMChart data={e1rmTrend} />
      </Card>

      {/* Weekly volume */}
      <Card title="Weekly Volume" hint="weight × reps">
        <VolumeChart data={weeklyVolume} />
      </Card>
    </div>
  );
}

import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";

const AXIS = "#6b6b6b";
const GRID = "#262626";
const tooltipStyle = {
  background: "#141414",
  border: "1px solid #262626",
  borderRadius: 8,
  fontSize: 12,
  color: "#f5f5f5",
};

function E1RMChart({ data }: { data: Record<string, number | string>[] }) {
  const colors: Record<string, string> = {
    "Back Squat": "var(--color-recovery)",
    "Bench Press": "var(--color-strain)",
    Deadlift: "var(--color-alert)",
    "Overhead Press": "var(--color-sleep)",
  };
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
          tickFormatter={(v: string) => v.slice(5)}
          minTickGap={24}
        />
        <YAxis stroke={AXIS} fontSize={10} tickLine={false} axisLine={false} width={36} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: GRID }} />
        <Legend wrapperStyle={{ fontSize: 11, color: "#a1a1a1" }} iconType="line" />
        {Object.keys(colors).map((lift) => (
          <Line
            key={lift}
            type="monotone"
            dataKey={lift}
            stroke={colors[lift]}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

import { BarChart, Bar } from "recharts";

function VolumeChart({ data }: { data: Record<string, number | string>[] }) {
  const groups = ["Legs", "Back", "Chest", "Shoulders"];
  const colors: Record<string, string> = {
    Legs: "var(--color-recovery)",
    Back: "var(--color-strain)",
    Chest: "var(--color-sleep)",
    Shoulders: "var(--color-warn)",
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
          tickFormatter={(v: string) => v.slice(5)}
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
