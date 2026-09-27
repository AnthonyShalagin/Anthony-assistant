"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

// Four places, named for what you want to know. Trends opens from Today.
const TABS = [
  { href: "/", label: "Today" },
  { href: "/strength", label: "Training" },
  { href: "/bloodwork", label: "Labs" },
  { href: "/goals", label: "Goals" },
];

const isAuthPage = (p: string | null) => p === "/login" || p === "/403" || !!p?.startsWith("/auth/");

export function Nav() {
  const pathname = usePathname();
  if (isAuthPage(pathname)) return null;
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" || pathname.startsWith("/trends") : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--color-border)] bg-[var(--color-bg)]/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-3xl items-center gap-2 px-4 py-2.5 sm:px-6">
        <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              aria-current={isActive(t.href) ? "page" : undefined}
              className={cn(
                "shrink-0 rounded-full px-3.5 py-1.5 text-[15px] transition-colors",
                isActive(t.href)
                  ? "bg-[var(--color-text)] font-medium text-[var(--color-bg)]"
                  : "text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
              )}
            >
              {t.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  const pathname = usePathname();
  if (isAuthPage(pathname)) return null;
  return (
    <footer className="mx-auto max-w-3xl px-4 pb-10 sm:px-6">
      <form action="/auth/signout" method="post">
        <button type="submit" className="text-[13px] text-[var(--color-text-dim)] hover:text-[var(--color-text)]">
          Sign out
        </button>
      </form>
    </footer>
  );
}
