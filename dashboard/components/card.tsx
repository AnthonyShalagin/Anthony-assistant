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
        "rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:p-5",
        className
      )}
    >
      {(title || hint) && (
        <div className="mb-4 flex items-baseline justify-between gap-3">
          {title && (
            <h3 className="text-[15px] font-semibold text-[var(--color-text)]">
              {title}
            </h3>
          )}
          {hint && (
            <span className="text-[13px] text-[var(--color-text-dim)]">{hint}</span>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
