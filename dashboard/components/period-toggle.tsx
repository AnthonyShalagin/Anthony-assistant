"use client";

import { cn } from "@/lib/cn";

export type Period = "D" | "W" | "M" | "Y";

export const PERIOD_DAYS: Record<Period, number> = {
  D: 1,
  W: 7,
  M: 30,
  Y: 365,
};

export const PERIOD_LABELS: Record<Period, string> = {
  D: "Day",
  W: "Week",
  M: "Month",
  Y: "Year",
};

export function PeriodToggle({
  value,
  onChange,
}: {
  value: Period;
  onChange: (p: Period) => void;
}) {
  const periods: Period[] = ["D", "W", "M", "Y"];
  return (
    <div className="inline-flex items-center gap-0.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] p-1">
      {periods.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            "rounded-full px-3 py-1 text-xs font-medium transition-colors min-w-[34px]",
            value === p
              ? "bg-[var(--color-text)] text-black"
              : "text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
          )}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
