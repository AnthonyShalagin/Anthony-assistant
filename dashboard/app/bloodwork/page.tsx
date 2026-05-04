import { Card } from "@/components/card";
import { getBloodwork } from "@/lib/mock";
import { cn } from "@/lib/cn";

export default function BloodworkPage() {
  const markers = getBloodwork();
  const panelDates = Array.from(new Set(markers.map((m) => m.panel_date))).sort();
  const latestDate = panelDates[panelDates.length - 1];
  const prevDate = panelDates[panelDates.length - 2];

  // Group by category, latest values
  const byCategory = new Map<string, typeof markers>();
  for (const m of markers) {
    if (m.panel_date !== latestDate) continue;
    const list = byCategory.get(m.category) ?? [];
    list.push(m);
    byCategory.set(m.category, list);
  }

  const prevByMarker = new Map(
    markers.filter((m) => m.panel_date === prevDate).map((m) => [m.marker, m])
  );

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Bloodwork</h1>
          <p className="mt-1 text-xs text-[var(--color-text-faint)]">
            Latest panel: {latestDate} · Previous: {prevDate}
          </p>
        </div>
        <button
          disabled
          className="rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-text-faint)]"
          title="Coming soon"
        >
          + Upload Panel
        </button>
      </div>

      {[...byCategory.entries()].map(([cat, list]) => (
        <section key={cat}>
          <h2 className="mb-3 text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-text-dim)]">
            {cat}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {list.map((m) => (
              <BiomarkerCard
                key={m.marker}
                marker={m.marker}
                value={m.value}
                unit={m.unit}
                ref_low={m.ref_low}
                ref_high={m.ref_high}
                status={m.status}
                prev={prevByMarker.get(m.marker)?.value}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function BiomarkerCard({
  marker,
  value,
  unit,
  ref_low,
  ref_high,
  status,
  prev,
}: {
  marker: string;
  value: number;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  status: "optimal" | "normal" | "high" | "low";
  prev?: number;
}) {
  const statusColor = {
    optimal: "var(--color-recovery)",
    normal: "var(--color-strain)",
    high: "var(--color-alert)",
    low: "var(--color-warn)",
  }[status];
  const statusLabel = status.toUpperCase();
  const delta = prev != null ? value - prev : null;
  const deltaPositive = delta != null && delta >= 0;
  // For markers where lower is better (LDL, ApoB, etc.) we'd flip, but keep simple.

  // Position on range bar
  const pct = (() => {
    if (ref_low == null && ref_high == null) return 50;
    const lo = ref_low ?? Math.max(0, value - (ref_high ?? value));
    const hi = ref_high ?? value * 1.5;
    const range = hi - lo || 1;
    return Math.max(0, Math.min(100, ((value - lo) / range) * 100));
  })();

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-medium text-[var(--color-text)]">{marker}</div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="metric-num text-2xl font-semibold" style={{ color: statusColor }}>
              {value}
            </span>
            <span className="text-xs text-[var(--color-text-faint)]">{unit}</span>
          </div>
        </div>
        <span
          className="rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wider"
          style={{ background: `${statusColor}22`, color: statusColor }}
        >
          {statusLabel}
        </span>
      </div>

      {/* Range bar */}
      <div className="mt-4">
        <div className="relative h-1.5 rounded-full bg-[var(--color-border)]">
          <div
            className="absolute -top-0.5 h-2.5 w-0.5 rounded"
            style={{ left: `${pct}%`, background: statusColor }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[10px] tabular-nums text-[var(--color-text-faint)]">
          <span>{ref_low ?? "—"}</span>
          <span>{ref_high ?? "—"}</span>
        </div>
      </div>

      {delta != null && (
        <div className="mt-3 text-xs">
          <span className={cn("tabular-nums", deltaPositive ? "text-[var(--color-warn)]" : "text-[var(--color-recovery)]")}>
            {deltaPositive ? "▲" : "▼"} {Math.abs(delta).toFixed(1)} {unit}
          </span>
          <span className="ml-1 text-[var(--color-text-faint)]">vs prev</span>
        </div>
      )}
    </div>
  );
}
