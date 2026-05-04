import { fetchBloodwork } from "@/lib/data";
import { cn } from "@/lib/cn";
import { BiomarkerCard } from "./biomarker-card";

export const dynamic = "force-dynamic";

export default async function BloodworkPage() {
  const markers = await fetchBloodwork();
  const panelDates = Array.from(new Set(markers.map((m) => m.panel_date))).sort();
  const latestDate = panelDates[panelDates.length - 1];

  // Build per-marker history: marker name -> array of {date, value, status}
  const historyByMarker = new Map<
    string,
    { date: string; value: number; status: string }[]
  >();
  for (const m of markers) {
    const list = historyByMarker.get(m.marker) ?? [];
    list.push({ date: m.panel_date, value: m.value, status: m.status });
    historyByMarker.set(m.marker, list);
  }
  for (const list of historyByMarker.values()) {
    list.sort((a, b) => a.date.localeCompare(b.date));
  }

  // Use the LATEST panel's metadata as the "current" snapshot for each marker
  const latestByMarker = new Map<string, (typeof markers)[number]>();
  for (const m of markers) {
    const cur = latestByMarker.get(m.marker);
    if (!cur || m.panel_date > cur.panel_date) {
      latestByMarker.set(m.marker, m);
    }
  }

  // Group latest snapshots by category
  const byCategory = new Map<string, (typeof markers)[number][]>();
  for (const m of latestByMarker.values()) {
    const list = byCategory.get(m.category) ?? [];
    list.push(m);
    byCategory.set(m.category, list);
  }
  // Sort categories: Heart and Metabolic first, rest alphabetical
  const CATEGORY_ORDER = ["Heart", "Metabolic", "Hormones", "Inflammation", "Nutrients", "Liver", "Kidney", "Electrolytes", "CBC", "Toxins", "Other"];
  const sortedCategories = [...byCategory.keys()].sort((a, b) => {
    const ai = CATEGORY_ORDER.indexOf(a);
    const bi = CATEGORY_ORDER.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Bloodwork</h1>
          <p className="mt-1 text-xs text-[var(--color-text-faint)]">
            {panelDates.length} panels · {latestByMarker.size} biomarkers · {markers.length} measurements
          </p>
          <p className="mt-1 text-xs text-[var(--color-text-faint)]">
            Latest panel: {latestDate} · History: {panelDates[0]} → {panelDates[panelDates.length - 1]}
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

      {sortedCategories.map((cat) => {
        const list = (byCategory.get(cat) ?? []).slice().sort((a, b) => a.marker.localeCompare(b.marker));
        return (
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
                  history={historyByMarker.get(m.marker) ?? []}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
