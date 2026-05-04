"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { getDef } from "@/lib/biomarker-info";
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

const CATEGORY_ORDER = [
  "Heart",
  "Metabolic",
  "Hormones",
  "Inflammation",
  "Nutrients",
  "Liver",
  "Kidney",
  "Electrolytes",
  "CBC",
  "Toxins",
  "Other",
];

type Bucket = "all" | "out" | "in" | "other";

export function BloodworkClient({ markers }: { markers: Marker[] }) {
  const [query, setQuery] = useState("");
  const [bucket, setBucket] = useState<Bucket>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("All");

  // Build per-marker history
  const historyByMarker = useMemo(() => {
    const m = new Map<string, { date: string; value: number; status: string }[]>();
    for (const x of markers) {
      const list = m.get(x.marker) ?? [];
      list.push({ date: x.panel_date, value: x.value, status: x.status });
      m.set(x.marker, list);
    }
    for (const list of m.values()) list.sort((a, b) => a.date.localeCompare(b.date));
    return m;
  }, [markers]);

  // Latest reading per marker
  const latestByMarker = useMemo(() => {
    const m = new Map<string, Marker>();
    for (const x of markers) {
      const cur = m.get(x.marker);
      if (!cur || x.panel_date > cur.panel_date) m.set(x.marker, x);
    }
    return m;
  }, [markers]);

  const allLatest = useMemo(() => [...latestByMarker.values()], [latestByMarker]);

  // Counts for the status pills
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

  // Categories present
  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const m of allLatest) set.add(m.category);
    return ["All", ...CATEGORY_ORDER.filter((c) => set.has(c)), ...[...set].filter((c) => !CATEGORY_ORDER.includes(c)).sort()];
  }, [allLatest]);

  // Filter
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return allLatest.filter((m) => {
      if (activeCategory !== "All" && m.category !== activeCategory) return false;
      if (bucket === "in" && !(m.status === "optimal" || m.status === "normal")) return false;
      if (bucket === "out" && !(m.status === "high" || m.status === "low")) return false;
      if (bucket === "other" && (m.status === "optimal" || m.status === "normal" || m.status === "high" || m.status === "low")) return false;
      if (q && !m.marker.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [allLatest, activeCategory, bucket, query]);

  // Group filtered by category for rendering
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

  return (
    <div className="space-y-6">
      {/* Header summary */}
      <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <div className="text-2xl font-semibold tracking-tight">{counts.all} Biomarkers</div>
          <div className="mt-4 flex items-end gap-8">
            <CountBar
              label="In Range"
              count={counts.in}
              total={counts.all}
              color="var(--color-recovery)"
            />
            <CountBar
              label="Out of Range"
              count={counts.out}
              total={counts.all}
              color="var(--color-alert)"
            />
            <CountBar
              label="Other"
              count={counts.other}
              total={counts.all}
              color="#6b6b6b"
            />
          </div>
          <div className="mt-4 text-xs text-[var(--color-text-faint)]">
            Latest panel: {latestDate} · History: {earliestDate} → {latestDate} · {panelDates.length} panels · {markers.length} measurements
          </div>
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
                    expanded={expanded === m.marker}
                    onToggle={() => setExpanded(expanded === m.marker ? null : m.marker)}
                    isLast={idx === list.length - 1}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
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
  expanded,
  onToggle,
  isLast,
}: {
  marker: Marker;
  history: { date: string; value: number; status: string }[];
  expanded: boolean;
  onToggle: () => void;
  isLast: boolean;
}) {
  const def = getDef(marker.marker);
  const color = STATUS_COLOR[marker.status] ?? "#6b6b6b";
  const display = def?.display ?? marker.marker;
  const inRange = marker.status === "optimal" || marker.status === "normal";

  return (
    <div className={cn("group", !isLast && "border-b border-[var(--color-border)]")}>
      <button
        onClick={onToggle}
        className="grid w-full grid-cols-[4px_1fr_auto] items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-[var(--color-surface-2)]"
      >
        {/* Status bar */}
        <span
          className="h-10 w-1 rounded-full"
          style={{ background: color }}
        />
        {/* Name + status */}
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-[var(--color-text)]">{display}</div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-[var(--color-text-dim)]">
            <span style={{ color }}>{inRange ? "In Range" : marker.status === "high" ? "Above Range" : marker.status === "low" ? "Below Range" : "Other"}</span>
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
      </button>

      {expanded && <DetailPanel marker={marker} history={history} />}
    </div>
  );
}

function Sparkline({
  history,
  color,
  refLow,
  refHigh,
}: {
  history: { date: string; value: number; status: string }[];
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

function DetailPanel({
  marker,
  history,
}: {
  marker: Marker;
  history: { date: string; value: number; status: string }[];
}) {
  const def = getDef(marker.marker);
  const color = STATUS_COLOR[marker.status] ?? "#6b6b6b";

  return (
    <div className="bg-[var(--color-surface-2)] px-6 py-5">
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        {/* Left: definition + range */}
        <div>
          {def?.description ? (
            <p className="text-sm leading-relaxed text-[var(--color-text-dim)]">{def.description}</p>
          ) : (
            <p className="text-sm italic text-[var(--color-text-faint)]">
              No description yet for this marker.
            </p>
          )}
          <div className="mt-4 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-[var(--color-text-faint)]">Reference range</span>
              <span className="metric-num tabular-nums text-[var(--color-text)]">
                {marker.ref_low != null && marker.ref_high != null
                  ? `${marker.ref_low}–${marker.ref_high}`
                  : marker.ref_high != null
                  ? `≤ ${marker.ref_high}`
                  : marker.ref_low != null
                  ? `≥ ${marker.ref_low}`
                  : "—"}{" "}
                {marker.unit}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-faint)]">Status</span>
              <span style={{ color }} className="font-medium uppercase tracking-wider">
                {marker.status}
              </span>
            </div>
            {def?.lowerIsBetter && (
              <div className="flex justify-between">
                <span className="text-[var(--color-text-faint)]">Direction</span>
                <span className="text-[var(--color-text-dim)]">Lower is better</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: trend chart */}
        <div className="-mx-2">
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={history} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`detail-${marker.marker.replace(/\W/g, "")}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                stroke="#6b6b6b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: string) => v.slice(2, 7)}
                minTickGap={20}
              />
              <YAxis
                stroke="#6b6b6b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              {marker.ref_low != null && (
                <ReferenceLine
                  y={marker.ref_low}
                  stroke="#3a3a3a"
                  strokeDasharray="3 3"
                  label={{ value: `≥ ${marker.ref_low}`, fill: "#6b6b6b", fontSize: 10, position: "insideLeft" }}
                />
              )}
              {marker.ref_high != null && (
                <ReferenceLine
                  y={marker.ref_high}
                  stroke="#3a3a3a"
                  strokeDasharray="3 3"
                  label={{ value: `≤ ${marker.ref_high}`, fill: "#6b6b6b", fontSize: 10, position: "insideLeft" }}
                />
              )}
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                fill={`url(#detail-${marker.marker.replace(/\W/g, "")})`}
                dot={(props: { cx?: number; cy?: number; payload?: { status: string }; index?: number }) => {
                  const { cx = 0, cy = 0, payload, index } = props;
                  const c = STATUS_COLOR[payload?.status ?? "normal"] ?? "#6b6b6b";
                  return (
                    <circle
                      key={`dot-${index ?? cx}-${cy}`}
                      cx={cx}
                      cy={cy}
                      r={3}
                      fill={c}
                      stroke="#0a0a0a"
                      strokeWidth={1}
                    />
                  );
                }}
                activeDot={{ r: 5 }}
              />
              <Tooltip
                cursor={{ stroke: "#262626" }}
                contentStyle={{
                  background: "#0a0a0a",
                  border: "1px solid #262626",
                  borderRadius: 6,
                  fontSize: 11,
                  color: "#f5f5f5",
                }}
                labelStyle={{ color: "#a1a1a1", fontSize: 10 }}
                formatter={(v) => [`${v}${marker.unit ? " " + marker.unit : ""}`, marker.marker] as [string, string]}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
