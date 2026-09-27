"use client";

import Link from "next/link";
import { useMemo } from "react";
import { Card } from "@/components/card";
import { displayName } from "@/lib/biomarker-info";
import {
  STATUS_VAR,
  avg,
  daysBetween,
  isOut,
  latestPerMarker,
  recoveryStatus,
  shortDate,
  sleepStatus,
  todayISO,
  vsBaseline,
  weekStart,
  type Status,
} from "@/lib/health";
import type { BloodMarker, InBodyScan } from "@/lib/mock";

type Day = {
  date: string;
  hrv: number | null;
  rhr: number | null;
  sleep_hours: number | null;
  steps: number | null;
  recovery_score: number | null;
  strain: number | null;
};

type Key = Exclude<keyof Day, "date">;

// Goals from Anthony's health plan
const LIFTS_PER_WEEK = 2;
const SLEEP_GOAL = 7.5;
const STEPS_GOAL = 8000;
const STALE_AFTER_DAYS = 1;

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function latestOf(days: Day[], key: Key): { value: number; date: string } | null {
  for (let i = days.length - 1; i >= 0; i--) {
    const v = days[i][key];
    if (v != null && !isNaN(Number(v)) && Number(v) !== 0) return { value: Number(v), date: days[i].date };
  }
  return null;
}

function headline(recovery: Status, sleep: Status): string {
  if (recovery === "good") return "Recovered. Good day for a hard session.";
  if (recovery === "watch") return "Middling recovery. Lift, but keep it moderate.";
  if (recovery === "bad") return "Run down. Rest or take a walk today.";
  if (sleep === "good") return "Slept well. No recovery score yet today.";
  if (sleep === "watch" || sleep === "bad") return "Short night. Take it easier today.";
  return "No new data yet today.";
}

export function TodayClient({
  metrics,
  inbody,
  sessionDates,
  markers,
}: {
  metrics: Day[];
  inbody: InBodyScan[];
  sessionDates: string[];
  markers: BloodMarker[];
}) {
  const today = todayISO();
  const days = useMemo(() => [...metrics].sort((a, b) => a.date.localeCompare(b.date)), [metrics]);

  // Latest value per metric, and whether its source has gone quiet
  const recovery = latestOf(days, "recovery_score");
  const sleep = latestOf(days, "sleep_hours");
  const hrv = latestOf(days, "hrv");
  const rhr = latestOf(days, "rhr");
  const strain = latestOf(days, "strain");
  const steps = latestOf(days, "steps");

  const whoopDate = recovery?.date ?? strain?.date ?? null;
  const ouraDate = [sleep?.date, hrv?.date].filter(Boolean).sort().pop() ?? null;
  const stale: string[] = [];
  if (!whoopDate || daysBetween(whoopDate, today) > STALE_AFTER_DAYS)
    stale.push(whoopDate ? `Whoop hasn't synced since ${shortDate(whoopDate)}.` : "No Whoop data yet.");
  if (!ouraDate || daysBetween(ouraDate, today) > STALE_AFTER_DAYS)
    stale.push(ouraDate ? `Oura hasn't synced since ${shortDate(ouraDate)}.` : "No Oura data yet.");
  const whoopFresh = whoopDate != null && daysBetween(whoopDate, today) <= STALE_AFTER_DAYS;

  const recStatus = whoopFresh ? recoveryStatus(recovery?.value ?? null) : "none";
  const slpStatus = sleepStatus(sleep?.value ?? null);

  const last30 = days.slice(-31, -1);
  const hrvVs = vsBaseline(hrv?.value ?? null, avg(last30.map((d) => d.hrv)));
  const rhrVs = vsBaseline(rhr?.value ?? null, avg(last30.map((d) => d.rhr)), false);

  // This week (Monday start)
  const monday = weekStart(today);
  const week = days.filter((d) => d.date >= monday);
  const lifts = sessionDates.filter((d) => d >= monday).length;
  const rawSleep = avg(week.map((d) => d.sleep_hours));
  const weekSleep = rawSleep == null ? null : Number(rawSleep.toFixed(1)); // compare what's shown
  const weekSteps = avg(week.map((d) => d.steps));
  const lastLift = sessionDates[sessionDates.length - 1];

  const scan = inbody[inbody.length - 1];
  const showScan = scan && daysBetween(scan.date, today) <= 60;

  const outOfRange = useMemo(() => latestPerMarker(markers).filter(isOut), [markers]);

  const now = new Date();
  const dateLine = `${WEEKDAYS[now.getDay()]}, ${MONTHS[now.getMonth()]} ${now.getDate()}`;
  const basis = [
    recStatus !== "none" && recovery ? `Whoop recovery ${Math.round(recovery.value)}%` : null,
    sleep ? `${sleep.value.toFixed(1)} h of sleep` : null,
  ].filter(Boolean);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Summary first: one sentence you can act on */}
      <header>
        <p className="text-[13px] font-medium text-[var(--color-text-dim)]">{dateLine}</p>
        <h1 className="mt-1 text-[28px] font-semibold leading-tight tracking-[-0.02em] sm:text-[34px]">
          {headline(recStatus, slpStatus)}
        </h1>
        {basis.length > 0 && (
          <p className="mt-2 text-[15px] text-[var(--color-text-dim)]">Based on {basis.join(" and ")}.</p>
        )}
        {stale.map((s) => (
          <p key={s} className="mt-1 text-[13px] font-medium" style={{ color: STATUS_VAR.watch }}>
            {s} Numbers below may be old.
          </p>
        ))}
      </header>

      {/* Three numbers that matter this morning */}
      <section className="grid grid-cols-3 gap-3">
        <Stat
          label="Recovery"
          value={recovery ? `${Math.round(recovery.value)}` : "–"}
          unit="%"
          status={recStatus}
          word={{ good: "Ready", watch: "Moderate", bad: "Low", none: "No data" }[recStatus]}
        />
        <Stat
          label="Sleep"
          value={sleep ? sleep.value.toFixed(1) : "–"}
          unit="h"
          status={slpStatus}
          word={{ good: "Enough", watch: "A bit short", bad: "Short", none: "No data" }[slpStatus]}
        />
        <Stat
          label="HRV"
          value={hrv ? `${Math.round(hrv.value)}` : "–"}
          unit="ms"
          status={hrvVs.status}
          word={hrvVs.word || "No data"}
        />
      </section>
      <p className="-mt-3 text-[13px] leading-snug text-[var(--color-text-dim)]">
        HRV is heart rate variability: higher usually means your body has recovered. It&apos;s compared with your
        own 30-day average, not other people&apos;s.
      </p>

      {/* This week vs the plan */}
      <Card title="This week" hint={`Since Monday, ${shortDate(monday)}`}>
        <ul className="divide-y divide-[var(--color-border)]">
          <WeekRow
            label="Lifts"
            value={`${lifts} this week · goal ${LIFTS_PER_WEEK}`}
            status={lifts >= LIFTS_PER_WEEK ? "good" : "watch"}
            word={lifts >= LIFTS_PER_WEEK ? "Done" : `${LIFTS_PER_WEEK - lifts} to go`}
          />
          <WeekRow
            label="Sleep"
            value={weekSleep ? `${weekSleep.toFixed(1)} h a night` : "–"}
            status={weekSleep == null ? "none" : weekSleep >= SLEEP_GOAL ? "good" : "watch"}
            word={weekSleep == null ? "No data" : weekSleep >= SLEEP_GOAL ? "On goal" : `Under ${SLEEP_GOAL} h goal`}
          />
          <WeekRow
            label="Steps"
            value={weekSteps ? `${Math.round(weekSteps).toLocaleString()} a day` : "–"}
            status={weekSteps == null ? "none" : weekSteps >= STEPS_GOAL ? "good" : "watch"}
            word={weekSteps == null ? "No data" : weekSteps >= STEPS_GOAL ? "On goal" : `Under ${STEPS_GOAL.toLocaleString()} goal`}
          />
        </ul>
      </Card>

      {/* Only when something needs a look */}
      {outOfRange.length > 0 && (
        <Card
          title={`${outOfRange.length} lab result${outOfRange.length > 1 ? "s" : ""} out of range`}
          hint={`Latest panel ${shortDate(outOfRange[0].panel_date)}`}
        >
          <ul className="space-y-1.5 text-[15px]">
            {outOfRange.slice(0, 3).map((m) => (
              <li key={m.marker} className="flex items-baseline justify-between gap-3">
                <span className="truncate">{displayName(m.marker)}</span>
                <span className="shrink-0 tabular-nums">
                  {m.value} {m.unit}{" "}
                  <span className="font-medium" style={{ color: STATUS_VAR.bad }}>
                    {m.status === "high" ? "High" : "Low"}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          <Link href="/bloodwork" className="mt-3 inline-block text-[15px] font-medium text-[var(--color-neutral)]">
            Review labs
          </Link>
        </Card>
      )}

      {/* Secondary detail, one line each */}
      <Card title="More from today">
        <ul className="divide-y divide-[var(--color-border)] text-[15px]">
          <DetailRow
            label="Resting heart rate"
            value={rhr ? `${Math.round(rhr.value)} bpm` : "–"}
            note={rhrVs.word ? `${rhrVs.word} · Oura` : "Oura"}
            status={rhrVs.status}
          />
          <DetailRow
            label="Strain"
            value={strain ? strain.value.toFixed(1) : "–"}
            note="Day's effort, 0 to 21 · Whoop"
          />
          <DetailRow label="Steps" value={steps ? Math.round(steps.value).toLocaleString() : "–"} note={steps ? `${shortDate(steps.date)} · Oura` : "Oura"} />
          <DetailRow label="Last lift" value={lastLift ? shortDate(lastLift) : "None logged"} note="Hevy" />
          {showScan && (
            <DetailRow
              label="Body scan"
              value={`${scan.weight_lbs.toFixed(1)} lb · ${scan.bf_pct.toFixed(1)}% fat`}
              note={`InBody, ${shortDate(scan.date)}`}
            />
          )}
        </ul>
        <Link href="/trends" className="mt-3 inline-block text-[15px] font-medium text-[var(--color-neutral)]">
          See trends
        </Link>
      </Card>
    </div>
  );
}

function Stat({ label, value, unit, status, word }: { label: string; value: string; unit: string; status: Status; word: string }) {
  return (
    <Link
      href="/trends"
      className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 transition-colors hover:bg-[var(--color-surface-2)] sm:p-4"
    >
      <div className="text-[13px] text-[var(--color-text-dim)]">{label}</div>
      <div className="mt-1 flex items-baseline gap-0.5">
        <span className="metric-num text-[26px] font-semibold leading-none sm:text-[32px]">{value}</span>
        {value !== "–" && <span className="text-[13px] text-[var(--color-text-dim)]">{unit}</span>}
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-[13px] font-medium" style={{ color: STATUS_VAR[status] }}>
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: STATUS_VAR[status] }} />
        <span className="truncate">{word}</span>
      </div>
    </Link>
  );
}

function WeekRow({ label, value, status, word }: { label: string; value: string; status: Status; word: string }) {
  return (
    <li className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
      <div>
        <div className="text-[15px]">{label}</div>
        <div className="metric-num text-[13px] text-[var(--color-text-dim)]">{value}</div>
      </div>
      <span className="flex items-center gap-1.5 text-[13px] font-medium" style={{ color: STATUS_VAR[status] }}>
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: STATUS_VAR[status] }} />
        {word}
      </span>
    </li>
  );
}

function DetailRow({ label, value, note, status }: { label: string; value: string; note: string; status?: Status }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <div>{label}</div>
        <div className="truncate text-[13px]" style={{ color: status && status !== "good" ? STATUS_VAR[status] : "var(--color-text-dim)" }}>
          {note}
        </div>
      </div>
      <span className="metric-num shrink-0 font-medium">{value}</span>
    </li>
  );
}
