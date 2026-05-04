// Mock data — replaced with Supabase queries once DB is wired.
// Shape matches the schema in supabase/migrations/0001_init.sql.

import { subDays, format } from "date-fns";

export type DailyMetric = {
  date: string; // yyyy-mm-dd
  hrv: number; // ms
  rhr: number; // bpm
  sleep_score: number; // 0-100
  sleep_hours: number;
  steps: number;
  recovery_score: number; // 0-100 (Whoop)
  strain: number; // 0-21 (Whoop)
};

export type SleepDetail = {
  date: string;
  deep_min: number;
  rem_min: number;
  light_min: number;
  awake_min: number;
  efficiency: number; // 0-100
};

export type StrongSet = {
  date: string;
  exercise: string;
  set_number: number;
  reps: number;
  weight_lbs: number;
  e1rm: number;
  muscle_group: string;
};

export type InBodyScan = {
  date: string;
  weight_lbs: number;
  bf_pct: number;
  skeletal_muscle_lbs: number;
};

export type BloodMarker = {
  panel_date: string;
  marker: string;
  value: number;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  status: "optimal" | "normal" | "high" | "low";
  category: string;
};

// ---------- Generators (deterministic-ish) ----------

const today = new Date("2026-05-03");

function rand(seed: number) {
  // Tiny seeded RNG for stable mock values
  let s = seed % 2147483647;
  return () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
}

export function getDailyMetrics(days = 90): DailyMetric[] {
  const r = rand(42);
  const out: DailyMetric[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = format(subDays(today, i), "yyyy-MM-dd");
    const baseHrv = 65 + Math.sin(i / 7) * 8;
    const baseRhr = 56 + Math.cos(i / 5) * 3;
    out.push({
      date: d,
      hrv: Math.round(baseHrv + (r() - 0.5) * 12),
      rhr: Math.round(baseRhr + (r() - 0.5) * 4),
      sleep_score: Math.round(78 + (r() - 0.5) * 20),
      sleep_hours: +(7 + (r() - 0.5) * 2).toFixed(1),
      steps: Math.round(8500 + (r() - 0.5) * 6000),
      recovery_score: Math.round(70 + (r() - 0.5) * 40),
      strain: +(12 + (r() - 0.5) * 8).toFixed(1),
    });
  }
  return out;
}

export function getTodayMetric(): DailyMetric {
  const all = getDailyMetrics(1);
  return all[0];
}

export function getSleepDetails(days = 30): SleepDetail[] {
  const r = rand(99);
  return Array.from({ length: days }, (_, i) => {
    const d = format(subDays(today, days - 1 - i), "yyyy-MM-dd");
    const deep = Math.round(80 + (r() - 0.5) * 30);
    const rem = Math.round(110 + (r() - 0.5) * 40);
    const light = Math.round(220 + (r() - 0.5) * 60);
    const awake = Math.round(20 + (r() - 0.5) * 15);
    const total = deep + rem + light;
    return {
      date: d,
      deep_min: deep,
      rem_min: rem,
      light_min: light,
      awake_min: Math.max(awake, 5),
      efficiency: Math.round((total / (total + awake)) * 100),
    };
  });
}

const EXERCISES = [
  { name: "Back Squat", group: "Legs", base: 285 },
  { name: "Bench Press", group: "Chest", base: 215 },
  { name: "Deadlift", group: "Back", base: 365 },
  { name: "Overhead Press", group: "Shoulders", base: 135 },
  { name: "Barbell Row", group: "Back", base: 185 },
  { name: "Pull-Up", group: "Back", base: 0 }, // bodyweight
  { name: "Romanian Deadlift", group: "Legs", base: 245 },
  { name: "Incline DB Press", group: "Chest", base: 75 },
];

export function getStrongSets(weeks = 12): StrongSet[] {
  const r = rand(7);
  const out: StrongSet[] = [];
  for (let w = weeks - 1; w >= 0; w--) {
    // Roughly 4 workouts per week, hit different exercises
    for (let day = 0; day < 4; day++) {
      const date = format(subDays(today, w * 7 + day * 2), "yyyy-MM-dd");
      const exs = EXERCISES.filter(() => r() > 0.55).slice(0, 3);
      for (const ex of exs) {
        const progress = (weeks - w) * 1.5; // slow gains over time
        for (let s = 1; s <= 4; s++) {
          const reps = 5 + Math.floor(r() * 4);
          const weight = ex.base
            ? Math.round(ex.base + progress + (r() - 0.5) * 10)
            : 0;
          // Epley formula for e1RM
          const e1rm = weight ? Math.round(weight * (1 + reps / 30)) : 0;
          out.push({
            date,
            exercise: ex.name,
            set_number: s,
            reps,
            weight_lbs: weight,
            e1rm,
            muscle_group: ex.group,
          });
        }
      }
    }
  }
  return out;
}

export function getInBodyScans(): InBodyScan[] {
  // Roughly monthly scans for the past 6 months
  return [
    { date: "2025-12-04", weight_lbs: 192.4, bf_pct: 19.2, skeletal_muscle_lbs: 89.1 },
    { date: "2026-01-08", weight_lbs: 190.8, bf_pct: 18.4, skeletal_muscle_lbs: 89.7 },
    { date: "2026-02-05", weight_lbs: 189.2, bf_pct: 17.6, skeletal_muscle_lbs: 90.2 },
    { date: "2026-03-07", weight_lbs: 187.9, bf_pct: 16.9, skeletal_muscle_lbs: 90.6 },
    { date: "2026-04-04", weight_lbs: 186.5, bf_pct: 16.2, skeletal_muscle_lbs: 91.0 },
    { date: "2026-05-01", weight_lbs: 185.2, bf_pct: 15.7, skeletal_muscle_lbs: 91.3 },
  ];
}

export function getBloodwork(): BloodMarker[] {
  // Two panels — 6mo apart, Function Health style
  const panels = [
    {
      date: "2025-11-15",
      values: {
        A1C: 5.2, ApoB: 88, LDL: 102, HDL: 54, Triglycerides: 95,
        TotalCholesterol: 175, Testosterone: 612, FreeT: 14.2,
        hsCRP: 0.8, FastingInsulin: 6.1, FastingGlucose: 91,
        Vitamin_D: 38, TSH: 1.9, Ferritin: 145,
      },
    },
    {
      date: "2026-04-20",
      values: {
        A1C: 5.0, ApoB: 76, LDL: 92, HDL: 58, Triglycerides: 82,
        TotalCholesterol: 166, Testosterone: 685, FreeT: 16.4,
        hsCRP: 0.5, FastingInsulin: 5.2, FastingGlucose: 88,
        Vitamin_D: 46, TSH: 1.7, Ferritin: 132,
      },
    },
  ];
  const meta: Record<string, { unit: string; low: number | null; high: number | null; cat: string }> = {
    A1C: { unit: "%", low: null, high: 5.6, cat: "Metabolic" },
    ApoB: { unit: "mg/dL", low: null, high: 90, cat: "Heart" },
    LDL: { unit: "mg/dL", low: null, high: 100, cat: "Heart" },
    HDL: { unit: "mg/dL", low: 40, high: null, cat: "Heart" },
    Triglycerides: { unit: "mg/dL", low: null, high: 150, cat: "Heart" },
    TotalCholesterol: { unit: "mg/dL", low: null, high: 200, cat: "Heart" },
    Testosterone: { unit: "ng/dL", low: 300, high: 1000, cat: "Hormones" },
    FreeT: { unit: "pg/mL", low: 9, high: 30, cat: "Hormones" },
    hsCRP: { unit: "mg/L", low: null, high: 1.0, cat: "Inflammation" },
    FastingInsulin: { unit: "uIU/mL", low: null, high: 8, cat: "Metabolic" },
    FastingGlucose: { unit: "mg/dL", low: 70, high: 99, cat: "Metabolic" },
    Vitamin_D: { unit: "ng/mL", low: 30, high: 100, cat: "Nutrients" },
    TSH: { unit: "mIU/L", low: 0.4, high: 4.0, cat: "Hormones" },
    Ferritin: { unit: "ng/mL", low: 30, high: 400, cat: "Nutrients" },
  };
  const out: BloodMarker[] = [];
  for (const p of panels) {
    for (const [marker, value] of Object.entries(p.values)) {
      const m = meta[marker];
      let status: BloodMarker["status"] = "optimal";
      if (m.high != null && value > m.high) status = "high";
      else if (m.low != null && value < m.low) status = "low";
      else status = "optimal";
      out.push({
        panel_date: p.date,
        marker: marker.replace("_", " "),
        value,
        unit: m.unit,
        ref_low: m.low,
        ref_high: m.high,
        status,
        category: m.cat,
      });
    }
  }
  return out;
}

// Goals
export type Goal = {
  metric: "steps" | "sleep" | "bf";
  label: string;
  target: number;
  unit: string;
  period: "weekly" | "monthly";
  comparison: "gte" | "lte";
};

export const GOALS: Goal[] = [
  { metric: "steps", label: "Steps", target: 8000, unit: "/day avg", period: "weekly", comparison: "gte" },
  { metric: "sleep", label: "Sleep", target: 7.5, unit: "hr/day avg", period: "weekly", comparison: "gte" },
  { metric: "bf", label: "Body Fat", target: 15, unit: "%", period: "monthly", comparison: "lte" },
];
