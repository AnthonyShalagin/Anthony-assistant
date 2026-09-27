// Shared rules for turning numbers into plain-language status. Every screen
// uses these so "good" means the same thing everywhere.

import { canonicalStatus, getDef } from "@/lib/biomarker-info";
import type { BloodMarker } from "@/lib/mock";

export type Status = "good" | "watch" | "bad" | "none";

export const STATUS_VAR: Record<Status, string> = {
  good: "var(--color-good)",
  watch: "var(--color-watch)",
  bad: "var(--color-bad)",
  none: "var(--color-text-faint)",
};

/** Whoop's own recovery bands: green 67+, yellow 34-66, red 0-33. */
export function recoveryStatus(v: number | null): Status {
  if (v == null) return "none";
  return v >= 67 ? "good" : v >= 34 ? "watch" : "bad";
}

export function sleepStatus(hours: number | null): Status {
  if (hours == null) return "none";
  return hours >= 7 ? "good" : hours >= 6 ? "watch" : "bad";
}

/** Compare to your own 30-day baseline; HRV is personal, not absolute. */
export function vsBaseline(v: number | null, base: number | null, higherIsBetter = true): { status: Status; word: string } {
  if (v == null || base == null || base === 0) return { status: "none", word: "" };
  const pct = ((v - base) / base) * 100 * (higherIsBetter ? 1 : -1);
  if (pct >= 5) return { status: "good", word: higherIsBetter ? "Above usual" : "Below usual" };
  if (pct <= -10) return { status: "watch", word: higherIsBetter ? "Below usual" : "Above usual" };
  return { status: "good", word: "Usual" };
}

export function avg(values: (number | null | undefined)[]): number | null {
  const ns = values.filter((v): v is number => v != null && !isNaN(Number(v)) && Number(v) !== 0).map(Number);
  return ns.length ? ns.reduce((a, b) => a + b, 0) / ns.length : null;
}

/** Monday of the week containing `iso`, as YYYY-MM-DD. */
export function weekStart(iso: string): string {
  const d = new Date(iso + "T12:00:00");
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  return d.toISOString().slice(0, 10);
}

export function todayISO(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function daysBetween(a: string, b: string): number {
  return Math.round((new Date(b + "T12:00:00").getTime() - new Date(a + "T12:00:00").getTime()) / 86400000);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "Sep 27" (adds the year only when it isn't this year). */
export function shortDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  const base = `${MONTHS[parseInt(m, 10) - 1]} ${parseInt(d, 10)}`;
  return y === todayISO().slice(0, 4) ? base : `${base}, ${y}`;
}

/** Lab ranges from lib/biomarker-info.ts override the lab's own, so status is consistent. */
type LabResult = { marker: string; value: number; ref_low: number | null; ref_high: number | null; status: string };

export function withCanonical<T extends LabResult>(m: T): T {
  const def = getDef(m.marker);
  if (!def) return m;
  return {
    ...m,
    ref_low: def.ref_low ?? m.ref_low,
    ref_high: def.ref_high ?? m.ref_high,
    status: canonicalStatus(m.marker, m.value),
  };
}

export function latestPerMarker(markers: BloodMarker[]): BloodMarker[] {
  const byMarker = new Map<string, BloodMarker>();
  for (const m of markers.map(withCanonical)) {
    const cur = byMarker.get(m.marker);
    if (!cur || m.panel_date > cur.panel_date) byMarker.set(m.marker, m);
  }
  return [...byMarker.values()];
}

export const isOut = (m: { status: string }) => m.status === "high" || m.status === "low";
