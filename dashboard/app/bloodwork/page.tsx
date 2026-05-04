import { fetchBloodwork } from "@/lib/data";
import { BloodworkClient, type Marker } from "./bloodwork-client";

export const dynamic = "force-dynamic";

export default async function BloodworkPage() {
  const markers = (await fetchBloodwork()) as Marker[];

  return (
    <div>
      <div className="mb-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Bloodwork</h1>
          <p className="mt-1 text-xs text-[var(--color-text-faint)]">
            Function-Health-style data view across all your panels.
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
      <BloodworkClient markers={markers} />
    </div>
  );
}
