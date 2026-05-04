"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { getDef, canonicalStatus } from "@/lib/biomarker-info";
import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

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

const STATUS_COLOR: Record<string, string> = {
  optimal: "var(--color-recovery)",
  normal: "var(--color-strain)",
  high: "var(--color-alert)",
  low: "var(--color-warn)",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Format an ISO date as "Jun '25". */
function formatShort(iso: string): string {
  const [y, m] = iso.split("-");
  const month = MONTHS[parseInt(m, 10) - 1] ?? m;
  return `${month} '${y.slice(2)}`;
}

/** Format an ISO date as "Jun 13, 2025". */
function formatFull(iso: string): string {
  const [y, m, d] = iso.split("-");
  const month = MONTHS[parseInt(m, 10) - 1] ?? m;
  return `${month} ${parseInt(d, 10)}, ${y}`;
}

const CATEGORY_ORDER = [
  "Heart",
  "Metabolic",
  "Hormones",
  "Male Health",
  "Inflammation",
  "Nutrients",
  "Liver",
  "Kidney",
  "Electrolytes",
  "CBC",
  "Urine",
  "Toxins",
  "Other",
];

type Bucket = "all" | "out" | "in" | "other";
type HistoryPoint = { date: string; value: number; status: string };

/**
 * Apply canonical reference ranges from biomarker-info.ts. This overrides
 * the per-panel ranges that come from the lab so status is consistent
 * across panels (otherwise the same value can be "in range" at one lab
 * and "out of range" at another).
 */
function applyCanonical(m: Marker): Marker {
  const def = getDef(m.marker);
  if (!def) return m;
  const ref_low = def.ref_low ?? m.ref_low;
  const ref_high = def.ref_high ?? m.ref_high;
  const status = canonicalStatus(m.marker, m.value);
  return { ...m, ref_low, ref_high, status };
}

export function BloodworkClient({ markers }: { markers: Marker[] }) {
  const normalized = useMemo(() => markers.map(applyCanonical), [markers]);

  const [query, setQuery] = useState("");
  const [bucket, setBucket] = useState<Bucket>("all");
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [hoveredMarker, setHoveredMarker] = useState<string | null>(null);
  const [hoverPos, setHoverPos] = useState<{ top: number; left: number } | null>(null);

  // Build per-marker history (using canonical statuses)
  const historyByMarker = useMemo(() => {
    const m = new Map<string, HistoryPoint[]>();
    for (const x of normalized) {
      const list = m.get(x.marker) ?? [];
      list.push({ date: x.panel_date, value: x.value, status: x.status });
      m.set(x.marker, list);
    }
    for (const list of m.values()) list.sort((a, b) => a.date.localeCompare(b.date));
    return m;
  }, [normalized]);

  // Latest reading per marker
  const latestByMarker = useMemo(() => {
    const m = new Map<string, Marker>();
    for (const x of normalized) {
      const cur = m.get(x.marker);
      if (!cur || x.panel_date > cur.panel_date) m.set(x.marker, x);
    }
    return m;
  }, [normalized]);

  const allLatest = useMemo(() => [...latestByMarker.values()], [latestByMarker]);

  const counts = useMemo(() => {
    let inRange = 0,
      outRange = 0,
      other = 0;
    for (const m of allLatest) {
      if (m.status === "optimal" || m.status === "normal") inRange++;
      else if (m.status === "high" || m.status === "low") outRange++;
      else other++;
    }
    return { all: allLatest.length, in: inRange, out: outRange, other };
  }, [allLatest]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const m of allLatest) set.add(m.category);
    return ["All", ...CATEGORY_ORDER.filter((c) => set.has(c)), ...[...set].filter((c) => !CATEGORY_ORDER.includes(c)).sort()];
  }, [allLatest]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return allLatest.filter((m) => {
      if (activeCategory !== "All" && m.category !== activeCategory) return false;
      if (bucket === "in" && !(m.status === "optimal" || m.status === "normal")) return false;
      if (bucket === "out" && !(m.status === "high" || m.status === "low")) return false;
      if (bucket === "other" && (m.status === "optimal" || m.status === "normal" || m.status === "high" || m.status === "low")) return false;
      if (q) {
        const def = getDef(m.marker);
        const display = (def?.display ?? m.marker).toLowerCase();
        if (!display.includes(q) && !m.marker.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [allLatest, activeCategory, bucket, query]);

  const groupedByCategory = useMemo(() => {
    const m = new Map<string, Marker[]>();
    for (const x of filtered) {
      const list = m.get(x.category) ?? [];
      list.push(x);
      m.set(x.category, list);
    }
    for (const list of m.values()) list.sort((a, b) => a.marker.localeCompare(b.marker));
    return [...m.entries()].sort((a, b) => {
      const ai = CATEGORY_ORDER.indexOf(a[0]);
      const bi = CATEGORY_ORDER.indexOf(b[0]);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
  }, [filtered]);

  const panelDates = useMemo(
    () => Array.from(new Set(markers.map((m) => m.panel_date))).sort(),
    [markers]
  );
  const latestDate = panelDates[panelDates.length - 1] ?? "—";
  const earliestDate = panelDates[0] ?? "—";

  const hoveredFull = hoveredMarker
    ? latestByMarker.get(hoveredMarker)
    : null;
  const hoveredHistory = hoveredMarker ? historyByMarker.get(hoveredMarker) ?? [] : [];

  return (
    <div className="space-y-6">
      {/* Header summary */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <div className="text-2xl font-semibold tracking-tight">{counts.all} Biomarkers</div>
        <div className="mt-4 flex items-end gap-8">
          <CountBar label="In Range" count={counts.in} total={counts.all} color="var(--color-recovery)" />
          <CountBar label="Out of Range" count={counts.out} total={counts.all} color="var(--color-alert)" />
          <CountBar label="Other" count={counts.other} total={counts.all} color="#6b6b6b" />
        </div>
        <div className="mt-4 text-xs text-[var(--color-text-faint)]">
          Latest panel: {latestDate} · History: {earliestDate} → {latestDate} · {panelDates.length} panels · {markers.length} measurements · canonical ranges applied
        </div>
      </div>

      {/* Search + status pills */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm">
          <Search className="h-3.5 w-3.5 text-[var(--color-text-faint)]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search biomarkers..."
            className="bg-transparent placeholder:text-[var(--color-text-faint)] outline-none w-44"
          />
        </div>
        <FilterPill active={bucket === "all"} onClick={() => setBucket("all")}>
          All · {counts.all}
        </FilterPill>
        <FilterPill active={bucket === "out"} onClick={() => setBucket("out")} dot="var(--color-alert)">
          Out of Range · {counts.out}
        </FilterPill>
        <FilterPill active={bucket === "in"} onClick={() => setBucket("in")} dot="var(--color-recovery)">
          In Range · {counts.in}
        </FilterPill>
        <FilterPill active={bucket === "other"} onClick={() => setBucket("other")} dot="#6b6b6b">
          Other · {counts.other}
        </FilterPill>
      </div>

      {/* Category tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-[var(--color-border)] pb-3">
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setActiveCategory(c)}
            className={cn(
              "rounded-full px-3 py-1 text-xs transition-colors",
              activeCategory === c
                ? "bg-[var(--color-text)] text-black"
                : "text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
            )}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Marker rows grouped by category */}
      {groupedByCategory.length === 0 ? (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center text-sm text-[var(--color-text-faint)]">
          No biomarkers match those filters.
        </div>
      ) : (
        <div className="space-y-8">
          {groupedByCategory.map(([cat, list]) => (
            <section key={cat}>
              <h2 className="mb-3 text-xs font-medium uppercase tracking-[0.2em] text-[var(--color-text-dim)]">
                {cat}
              </h2>
              <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
                {list.map((m, idx) => (
                  <MarkerRow
                    key={m.marker}
                    marker={m}
                    history={historyByMarker.get(m.marker) ?? []}
                    isLast={idx === list.length - 1}
                    onHoverEnter={(rect) => {
                      setHoveredMarker(m.marker);
                      // Estimated popover dimensions
                      const POP_W = 540;
                      const POP_H = 340;
                      const GAP = 12;
                      const PAD = 8;
                      // Prefer right of row; fall back to left if no space
                      let left = rect.right + GAP;
                      if (left + POP_W + PAD > window.innerWidth) {
                        left = rect.left - POP_W - GAP;
                      }
                      // If there's still no horizontal room either side, pin to right edge
                      if (left < PAD) left = window.innerWidth - POP_W - PAD;
                      // Vertically center on the row, then clamp inside viewport
                      let top = rect.top + rect.height / 2 - POP_H / 2;
                      top = Math.max(PAD, Math.min(top, window.innerHeight - POP_H - PAD));
                      setHoverPos({ top, left });
                    }}
                    onHoverLeave={() => {
                      setHoveredMarker(null);
                      setHoverPos(null);
                    }}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {/* Floating hover popover */}
      {hoveredFull && hoverPos && (
        <HoverPopover
          marker={hoveredFull}
          history={hoveredHistory}
          top={hoverPos.top}
          left={hoverPos.left}
        />
      )}
    </div>
  );
}

function CountBar({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex flex-col">
      <div className="metric-num text-2xl font-semibold">{count}</div>
      <div className="text-[11px] text-[var(--color-text-dim)]">{label}</div>
      <div
        className="mt-2 w-12 rounded"
        style={{ height: `${Math.max(8, pct * 0.6)}px`, background: color, opacity: 0.85 }}
      />
    </div>
  );
}

function FilterPill({
  active,
  onClick,
  children,
  dot,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  dot?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors",
        active
          ? "border-[var(--color-text)] bg-[var(--color-surface)] text-[var(--color-text)]"
          : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
      )}
    >
      {dot && (
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: dot }}
        />
      )}
      {children}
    </button>
  );
}

function MarkerRow({
  marker,
  history,
  isLast,
  onHoverEnter,
  onHoverLeave,
}: {
  marker: Marker;
  history: HistoryPoint[];
  isLast: boolean;
  onHoverEnter: (rect: DOMRect) => void;
  onHoverLeave: () => void;
}) {
  const def = getDef(marker.marker);
  const color = STATUS_COLOR[marker.status] ?? "#6b6b6b";
  const display = def?.display ?? marker.marker;
  const inRange = marker.status === "optimal" || marker.status === "normal";

  return (
    <div
      className={cn(
        "group grid grid-cols-[4px_1fr_auto] items-center gap-4 px-4 py-3 transition-colors hover:bg-[var(--color-surface-2)] cursor-default",
        !isLast && "border-b border-[var(--color-border)]"
      )}
      onMouseEnter={(e) => onHoverEnter(e.currentTarget.getBoundingClientRect())}
      onMouseLeave={onHoverLeave}
    >
      {/* Status bar */}
      <span className="h-10 w-1 rounded-full" style={{ background: color }} />
      {/* Name + status */}
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-[var(--color-text)]">{display}</div>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-[var(--color-text-dim)]">
          <span style={{ color }}>
            {inRange ? "In Range" : marker.status === "high" ? "Above Range" : marker.status === "low" ? "Below Range" : "Other"}
          </span>
          <span>·</span>
          <span className="metric-num tabular-nums text-[var(--color-text)]">
            {marker.value}
            {marker.unit ? ` ${marker.unit}` : ""}
          </span>
        </div>
      </div>
      {/* Mini sparkline */}
      {history.length >= 2 ? (
        <div className="hidden h-8 w-32 sm:block">
          <Sparkline history={history} color={color} refLow={marker.ref_low} refHigh={marker.ref_high} />
        </div>
      ) : (
        <span className="text-[10px] text-[var(--color-text-faint)]">single panel</span>
      )}
    </div>
  );
}

function Sparkline({
  history,
  color,
  refLow,
  refHigh,
}: {
  history: HistoryPoint[];
  color: string;
  refLow: number | null;
  refHigh: number | null;
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={history} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
        <defs>
          <linearGradient id={`spark-${color.replace(/\W/g, "")}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.4} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" hide />
        <YAxis hide domain={["dataMin - 1", "dataMax + 1"]} />
        {refLow != null && <ReferenceLine y={refLow} stroke="#3a3a3a" strokeDasharray="2 2" />}
        {refHigh != null && <ReferenceLine y={refHigh} stroke="#3a3a3a" strokeDasharray="2 2" />}
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#spark-${color.replace(/\W/g, "")})`}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function HoverPopover({
  marker,
  history,
  top,
  left,
}: {
  marker: Marker;
  history: HistoryPoint[];
  top: number;
  left: number;
}) {
  const def = getDef(marker.marker);
  const display = def?.display ?? marker.marker;
  const color = STATUS_COLOR[marker.status] ?? "#6b6b6b";

  return (
    <div
      className="pointer-events-none fixed z-50 w-[540px] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-6 shadow-2xl"
      style={{ top, left }}
    >
      <div className="flex items-baseline gap-2">
        <span className="text-base font-semibold text-[var(--color-text)]">{display}</span>
        <span
          className="rounded px-2 py-0.5 text-[11px] font-medium tracking-wider"
          style={{ background: `${color}22`, color }}
        >
          {marker.status.toUpperCase()}
        </span>
      </div>
      {def?.description && (
        <p className="mt-3 text-sm leading-relaxed text-[var(--color-text-dim)]">
          {def.description}
        </p>
      )}

      <div className="mt-5 grid grid-cols-[auto_1fr] gap-5 items-center">
        <ZoneBars marker={marker} />
        <div className="-ml-2">
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={history} margin={{ top: 28, right: 16, left: 8, bottom: 4 }}>
              <defs>
                <linearGradient id={`pop-${marker.marker.replace(/\W/g, "")}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                stroke="#a1a1a1"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatShort}
                interval={0}
                padding={{ left: 28, right: 28 }}
                tickMargin={6}
              />
              <YAxis hide domain={getDomain(marker, history)} />
              {marker.ref_low != null && (
                <ReferenceLine y={marker.ref_low} stroke="#3a3a3a" strokeDasharray="3 3" />
              )}
              {marker.ref_high != null && (
                <ReferenceLine y={marker.ref_high} stroke="#3a3a3a" strokeDasharray="3 3" />
              )}
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                fill={`url(#pop-${marker.marker.replace(/\W/g, "")})`}
                dot={(props: { cx?: number; cy?: number; payload?: HistoryPoint; index?: number }) => {
                  const { cx = 0, cy = 0, payload, index } = props;
                  const c = STATUS_COLOR[payload?.status ?? "normal"] ?? "#6b6b6b";
                  // Stagger value labels above/below to avoid overlap
                  const labelY = (index ?? 0) % 2 === 0 ? cy - 10 : cy - 10;
                  return (
                    <g key={`d-${index ?? cx}-${cy}`}>
                      <circle
                        cx={cx}
                        cy={cy}
                        r={4}
                        fill={c}
                        stroke="#0a0a0a"
                        strokeWidth={2}
                      />
                      <text
                        x={cx}
                        y={labelY}
                        textAnchor="middle"
                        fontSize={11}
                        fill={c}
                        fontWeight={600}
                      >
                        {payload?.value}
                      </text>
                    </g>
                  );
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] tabular-nums text-[var(--color-text-dim)]">
        <span>
          Latest{" "}
          <span className="metric-num text-[var(--color-text)] text-sm">
            {marker.value}
            {marker.unit ? ` ${marker.unit}` : ""}
          </span>{" "}
          <span className="text-[var(--color-text-faint)]">· {formatFull(marker.panel_date)}</span>
        </span>
        <span className="text-[var(--color-text-faint)]">
          {marker.ref_low != null && marker.ref_high != null
            ? `Range ${marker.ref_low}–${marker.ref_high}${marker.unit ? ` ${marker.unit}` : ""}`
            : marker.ref_high != null
            ? `≤ ${marker.ref_high}${marker.unit ? ` ${marker.unit}` : ""}`
            : marker.ref_low != null
            ? `≥ ${marker.ref_low}${marker.unit ? ` ${marker.unit}` : ""}`
            : ""}
        </span>
      </div>
    </div>
  );
}

function ZoneBars({ marker }: { marker: Marker }) {
  // Vertical zone visualization like Function Health: stacked colored zones
  // representing Above / In / Below range. The "current" zone is highlighted.
  const zones: { label: string; key: string; color: string }[] = [];
  if (marker.ref_high != null) {
    zones.push({ label: "Above Range", key: "high", color: "var(--color-alert)" });
  }
  zones.push({ label: "In Range", key: "in", color: "var(--color-recovery)" });
  if (marker.ref_low != null) {
    zones.push({ label: "Below Range", key: "low", color: "var(--color-warn)" });
  }

  const isCurrent = (key: string) => {
    if (key === "high") return marker.status === "high";
    if (key === "low") return marker.status === "low";
    return marker.status === "optimal" || marker.status === "normal";
  };

  return (
    <div className="flex flex-col gap-2.5">
      {zones.map((z) => (
        <div key={z.key} className="flex items-center gap-2.5">
          <div
            className="h-8 w-1.5 rounded"
            style={{
              background: z.color,
              opacity: isCurrent(z.key) ? 1 : 0.25,
            }}
          />
          <span
            className="text-xs"
            style={{
              color: isCurrent(z.key) ? z.color : "var(--color-text-faint)",
              fontWeight: isCurrent(z.key) ? 600 : 400,
            }}
          >
            {z.label}
          </span>
        </div>
      ))}
    </div>
  );
}

function getDomain(marker: Marker, history: HistoryPoint[]): [number, number] {
  const values = history.map((h) => h.value);
  const refs = [marker.ref_low, marker.ref_high].filter((x): x is number => x != null);
  const all = [...values, ...refs];
  if (all.length === 0) return [0, 1];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const pad = Math.max((max - min) * 0.15, 0.5);
  return [min - pad, max + pad];
}
