import { StrengthClient } from "./strength-client";
import { fetchStrongSets } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function TrainingPage() {
  // 26 weeks: enough history for 3-month change on each lift
  const sets = await fetchStrongSets(26);
  return <StrengthClient sets={sets} />;
}
