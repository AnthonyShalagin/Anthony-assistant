import { StrengthClient } from "./strength-client";
import { fetchStrongSets } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function StrengthPage() {
  const sets = await fetchStrongSets(12);
  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Strength</h1>
        <span className="text-xs text-[var(--color-text-faint)]">
          {sets.length} sets · last 12 wk
        </span>
      </div>

      <StrengthClient sets={sets} />
    </div>
  );
}
