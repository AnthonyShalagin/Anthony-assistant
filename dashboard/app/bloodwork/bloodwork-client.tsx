"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { cn } from "@/lib/cn";
import { displayName, getDef } from "@/lib/biomarker-info";
import { STATUS_VAR, isOut, shortDate, withCanonical, type Status } from "@/lib/health";

export type Marker = {
  panel_date: string;
  marker: string;
  value: number;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  status: "optimal" | "normal" | "high" | "low" | string;
  category: string;
};

const CATEGORY_ORDER = [
  "Heart", "Metabolic", "Hormones", "Male Health", "Inflammation", "Nutrients",
  "Liver", "Kidney", "Electrolytes", "CBC", "Urine", "Toxins", "Other",
];

type Point = { date: string; value: number; status: string };

const hasRange = (m: Marker) => m.ref_low != null || m.ref_high != null;

function statusOf(m: Marker): Status {
  if (isOut(m)) return "bad";
  return hasRange(m) ? "good" : "none";
}

function statusWord(m: Marker): string {
  if (m.status === "high") return "High";
  if (m.status === "low") return "Low";
  return hasRange(m) ? "In range" : "No range";
}

function rangeText(m: Marker): string {
  const u = m.unit ? ` ${m.unit}` : "";
  if (m.ref_low != null && m.ref_high != null) return `${m.ref_low} to ${m.ref_high}${u}`;
  if (m.ref_high != null) return `Under ${m.ref_high}${u}`;
  if (m.ref_low != null) return `Over ${m.ref_low}${u}`;
  return "";
}

export function BloodworkClient({ markers }: { markers: Marker[] }) {
  const normalized = useMemo(() => markers.map(withCanonical), [markers]);
  const [query, setQuery] = useState("");
  const [onlyOut, setOnlyOut] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const history = useMemo(() => {
    const h = new Map<string, Point[]>();
    for (const x of normalized) {
      const list = h.get(x.marker) ?? [];
      list.push({ date: x.panel_date, value: x.value, status: x.status });
      h.set(x.marker, list);
    }
    for (const list of h.values()) list.sort((a, b) => a.date.localeCompare(b.date));
    return h;
  }, [normalized]);

  const latest = useMemo(() => {
    const m = new Map<string, Marker>();
    for (const x of normalized) {
      const cur = m.get(x.marker);
      if (!cur || x.panel_date > cur.panel_date) m.set(x.marker, x);
    }
    return [...m.values()];
  }, [normalized]);

  const out = latest.filter((m) => isOut(m));
  const withRange = latest.filter(hasRange);
  const inRange = withRange.length - out.length;
  const panelDates = [...new Set(markers.map((m) => m.panel_date))].sort();
  const latestDate = panelDates[panelDates.length - 1];

  const q = query.trim().toLowerCase();
  const visible = latest.filter((m) => {
    if (onlyOut && !isOut(m)) return false;
    if (q && !displayName(m.marker).toLowerCase().includes(q) && !m.marker.toLowerCase().includes(q)) return false;
    return true;
  });

  const groups = useMemo(() => {
    const g = new Map<string, Marker[]>();
    for (const m of visible) {
      if (!onlyOut && !q && isOut(m)) continue; // shown in the section above
      const list = g.get(m.category) ?? [];
      list.push(m);
      g.set(m.category, list);
    }
    for (const list of g.values()) list.sort((a, b) => displayName(a.marker).localeCompare(displayName(b.marker)));
    const rank = (c: string) => (CATEGORY_ORDER.indexOf(c) + 1 || 99);
    return [...g.entries()].sort((a, b) => rank(a[0]) - rank(b[0]));
  }, [visible, onlyOut, q]);

  const openMarker = open ? latest.find((m) => m.marker === open) ?? null : null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-[28px] font-semibold tracking-[-0.02em] sm:text-[34px]">
          {out.length === 0 ? "All labs in range" : `${out.length} lab result${out.length > 1 ? "s" : ""} to watch`}
        </h1>
        <p className="mt-1 text-[15px] text-[var(--color-text-dim)]">
          {inRange} of {withRange.length} in range
          {latestDate ? ` · latest panel ${shortDate(latestDate)}` : ""}
        </p>
        {withRange.length > 0 && (
          <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-[var(--color-surface-2)]" aria-hidden>
            <div style={{ width: `${(inRange / withRange.length) * 100}%`, background: "var(--color-good)" }} />
            <div style={{ width: `${(out.length / withRange.length) * 100}%`, background: "var(--color-bad)" }} />
          </div>
        )}
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex rounded-full bg-[var(--color-surface-2)] p-0.5" role="tablist" aria-label="Filter">
          {[
            { label: "All", v: false },
            { label: `Out of range (${out.length})`, v: true },
          ].map((t) => (
            <button
              key={t.label}
              role="tab"
              aria-selected={onlyOut === t.v}
              onClick={() => setOnlyOut(t.v)}
              className={cn(
                "rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors",
                onlyOut === t.v ? "bg-[var(--color-surface)] text-[var(--color-text)] shadow-sm" : "text-[var(--color-text-dim)]"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
        <label className="flex min-w-0 flex-1 items-center gap-2 rounded-full bg-[var(--color-surface-2)] px-3 py-1.5 text-[15px] sm:max-w-xs">
          <Search className="h-4 w-4 shrink-0 text-[var(--color-text-dim)]" aria-hidden />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search labs"
            aria-label="Search labs"
            className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-[var(--color-text-dim)]"
          />
        </label>
      </div>

      {!onlyOut && !q && out.length > 0 && <Group title="Out of range" markers={out} history={history} onOpen={setOpen} />}
      {groups.map(([cat, list]) => (
        <Group key={cat} title={cat} markers={list} history={history} onOpen={setOpen} />
      ))}
      {visible.length === 0 && (
        <p className="rounded-2xl bg-[var(--color-surface)] p-6 text-center text-[15px] text-[var(--color-text-dim)]">
          No labs match that search.
        </p>
      )}

      <p className="text-[13px] text-[var(--color-text-dim)]">
        Ranges come from your health plan, which can be stricter than the lab&apos;s. Select a result to see what it
        means and how it has changed.
      </p>

      {openMarker && (
        <Detail marker={openMarker} history={history.get(openMarker.marker) ?? []} onClose={() => setOpen(null)} />
      )}
    </div>
  );
}

function Group({
  title,
  markers,
  history,
  onOpen,
}: {
  title: string;
  markers: Marker[];
  history: Map<string, Point[]>;
  onOpen: (m: string) => void;
}) {
  return (
    <section>
      <h2 className="mb-2 text-[13px] font-medium text-[var(--color-text-dim)]">
        {title}
        {title !== "Out of range" && ` · ${markers.length}`}
      </h2>
      <ul className="divide-y divide-[var(--color-border)] overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]">
        {markers.map((m) => (
          <li key={m.marker}>
            <button
              onClick={() => onOpen(m.marker)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--color-surface-2)]"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-[15px]">{displayName(m.marker)}</div>
                <div className="mt-0.5 text-[13px] font-medium" style={{ color: STATUS_VAR[statusOf(m)] }}>
                  {statusWord(m)}
                  {(history.get(m.marker)?.length ?? 0) > 1 && (
                    <span className="font-normal text-[var(--color-text-dim)]"> · {history.get(m.marker)!.length} results</span>
                  )}
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1.5">
                <span className="metric-num text-[15px] font-medium">
                  {m.value} <span className="text-[13px] font-normal text-[var(--color-text-dim)]">{m.unit}</span>
                </span>
                <RangeBar marker={m} className="w-20" />
              </div>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Where the value sits relative to the range: gray track, green in-range zone, dot for you. */
function RangeBar({ marker: m, className, large }: { marker: Marker; className?: string; large?: boolean }) {
  if (!hasRange(m)) return null;
  const lo = m.ref_low ?? 0;
  const hi = m.ref_high ?? lo * 2;
  const span = Math.max(hi - lo, 1);
  const min = Math.min(m.ref_low != null ? lo - span * 0.5 : 0, m.value);
  const max = Math.max(hi + span * 0.5, m.value);
  const pos = (v: number) => `${((v - min) / (max - min)) * 100}%`;
  const color = STATUS_VAR[statusOf(m)];
  return (
    <div className={cn("relative rounded-full bg-[var(--color-surface-2)]", large ? "h-2.5" : "h-1.5", className)} aria-hidden>
      <div
        className="absolute inset-y-0 rounded-full"
        style={{ left: pos(m.ref_low ?? min), right: `calc(100% - ${pos(m.ref_high ?? max)})`, background: "color-mix(in srgb, var(--color-good) 35%, transparent)" }}
      />
      <div
        className={cn("absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-[var(--color-surface)]", large ? "h-4 w-4" : "h-2.5 w-2.5")}
        style={{ left: pos(m.value), background: color }}
      />
    </div>
  );
}

function Detail({ marker: m, history, onClose }: { marker: Marker; history: Point[]; onClose: () => void }) {
  const def = getDef(m.marker);
  const color = STATUS_VAR[statusOf(m)];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const values = history.map((h) => h.value);
  const lo = Math.min(...values, m.ref_low ?? Infinity);
  const hi = Math.max(...values, m.ref_high ?? -Infinity);
  const pad = Math.max((hi - lo) * 0.1, 1);
  const floor = Math.max(0, lo - pad); // lab values are never negative

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true" aria-label={displayName(m.marker)}>
      <button className="absolute inset-0 bg-black/40" aria-label="Close" onClick={onClose} />
      <div className="relative max-h-[88vh] w-full overflow-y-auto rounded-t-3xl bg-[var(--color-surface)] p-5 pb-8 shadow-2xl sm:max-w-lg sm:rounded-3xl sm:pb-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-[22px] font-semibold leading-tight">{displayName(m.marker)}</h2>
            <p className="mt-0.5 text-[15px] font-medium" style={{ color }}>
              {statusWord(m)}
            </p>
          </div>
          <button onClick={onClose} className="rounded-full bg-[var(--color-surface-2)] p-1.5 text-[var(--color-text-dim)]" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 flex items-baseline gap-1.5">
          <span className="metric-num text-[34px] font-semibold leading-none">{m.value}</span>
          <span className="text-[15px] text-[var(--color-text-dim)]">{m.unit}</span>
          <span className="ml-auto text-[13px] text-[var(--color-text-dim)]">{shortDate(m.panel_date)}</span>
        </div>
        {hasRange(m) && (
          <div className="mt-4">
            <RangeBar marker={m} large />
            <p className="mt-2 text-[13px] text-[var(--color-text-dim)]">Goal range: {rangeText(m)}</p>
          </div>
        )}

        {def?.description && (
          <div className="mt-5">
            <h3 className="text-[15px] font-semibold">Why it matters</h3>
            <p className="mt-1 text-[15px] leading-relaxed text-[var(--color-text-dim)]">{def.description}</p>
          </div>
        )}

        {history.length > 1 && (
          <div className="mt-5">
            <h3 className="text-[15px] font-semibold">Your results</h3>
            <div className="mt-2 h-40">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                  {hasRange(m) && (
                    <ReferenceArea
                      y1={m.ref_low ?? floor}
                      y2={m.ref_high ?? hi + pad}
                      fill="var(--color-good)"
                      fillOpacity={0.08}
                      ifOverflow="extendDomain"
                    />
                  )}
                  <XAxis dataKey="date" tickFormatter={shortDate} tickLine={false} axisLine={false} fontSize={11} stroke="var(--color-text-dim)" minTickGap={24} />
                  <YAxis domain={[floor, hi + pad]} tickCount={3} tickLine={false} axisLine={false} fontSize={11} stroke="var(--color-text-dim)" width={44} tickFormatter={(v: number) => String(Math.round(v))} />
                  <Tooltip
                    contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 13, color: "var(--color-text)" }}
                    labelFormatter={(l) => shortDate(String(l))}
                    formatter={(v) => [`${v} ${m.unit}`, "Result"]}
                  />
                  <Line
                    dataKey="value"
                    stroke="var(--color-chart)"
                    strokeWidth={1.5}
                    isAnimationActive={false}
                    dot={(p: { cx?: number; cy?: number; payload?: Point; index?: number }) => (
                      <circle
                        key={p.index}
                        cx={p.cx}
                        cy={p.cy}
                        r={4}
                        fill={p.payload?.status === "high" || p.payload?.status === "low" ? "var(--color-bad)" : "var(--color-good)"}
                        stroke="var(--color-surface)"
                        strokeWidth={2}
                      />
                    )}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
