import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

export function Card({
  children,
  className,
  title,
  hint,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  hint?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5",
        className
      )}
    >
      {(title || hint) && (
        <div className="mb-4 flex items-baseline justify-between">
          {title && (
            <h3 className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
              {title}
            </h3>
          )}
          {hint && (
            <span className="text-xs text-[var(--color-text-faint)]">{hint}</span>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  unit,
  delta,
  accent,
  hint,
}: {
  label: string;
  value: string | number;
  unit?: string;
  delta?: { value: string; positive: boolean };
  accent?: "recovery" | "strain" | "sleep" | "alert" | "warn";
  hint?: string;
}) {
  const accentColor = accent
    ? `var(--color-${accent})`
    : "var(--color-text)";
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
        {label}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span
          className="metric-num text-4xl font-semibold leading-none"
          style={{ color: accentColor }}
        >
          {value}
        </span>
        {unit && (
          <span className="text-sm text-[var(--color-text-faint)]">{unit}</span>
        )}
      </div>
      {(delta || hint) && (
        <div className="mt-3 flex items-center justify-between text-xs">
          {delta ? (
            <span
              className={cn(
                "tabular-nums",
                delta.positive ? "text-[var(--color-recovery)]" : "text-[var(--color-alert)]"
              )}
            >
              {delta.positive ? "▲" : "▼"} {delta.value}
            </span>
          ) : (
            <span />
          )}
          {hint && (
            <span className="text-[var(--color-text-faint)]">{hint}</span>
          )}
        </div>
      )}
    </div>
  );
}
