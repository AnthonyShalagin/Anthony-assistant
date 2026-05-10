import { StrengthClient } from "./strength-client";
import { fetchStrongSets } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function StrengthPage() {
  // 26 weeks gives the priority-lift weighting tiers (4w, 12w, 26w) full
  // history to differentiate recent vs older work.
  const sets = await fetchStrongSets(26);
  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Strength</h1>
        <span className="text-xs text-[var(--color-text-faint)]">
          {sets.length} sets · last 6 mo
        </span>
      </div>

      <StrengthClient sets={sets} />
    </div>
  );
}
