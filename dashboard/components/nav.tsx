"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

const TABS = [
  { href: "/", label: "Today" },
  { href: "/trends", label: "Trends" },
  { href: "/strength", label: "Strength" },
  { href: "/bloodwork", label: "Bloodwork" },
  { href: "/goals", label: "Goals" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--color-border)] bg-[var(--color-bg)]/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[var(--color-recovery)] shadow-[0_0_10px_var(--color-recovery)]" />
          <span className="text-sm font-semibold tracking-[0.3em] text-[var(--color-text)] uppercase">
            Anthony
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {TABS.map((t) => {
            const active = t.href === "/" ? pathname === "/" : pathname.startsWith(t.href);
            return (
              <Link
                key={t.href}
                href={t.href}
                className={cn(
                  "rounded px-3 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-[var(--color-surface)] text-[var(--color-text)]"
                    : "text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
                )}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
        <div className="text-xs text-[var(--color-text-faint)] tabular-nums">
          {new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
        </div>
      </div>
    </header>
  );
}
