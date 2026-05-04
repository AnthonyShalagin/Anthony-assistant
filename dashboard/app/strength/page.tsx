import { Card } from "@/components/card";
import { StrengthClient } from "./strength-client";
import { getStrongSets } from "@/lib/mock";

export default function StrengthPage() {
  const sets = getStrongSets(12);
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
