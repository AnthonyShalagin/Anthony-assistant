import { fetchDailyMetrics } from "@/lib/data";
import { TrendsClient } from "./trends-client";

export const dynamic = "force-dynamic";

export default async function TrendsPage() {
  const data = await fetchDailyMetrics(400);
  return (
    <TrendsClient
      metrics={data.map((d) => ({
        date: d.date,
        hrv: d.hrv ?? null,
        rhr: d.rhr ?? null,
        sleep_score: d.sleep_score ?? null,
        sleep_hours: d.sleep_hours ?? null,
        steps: d.steps ?? null,
        recovery_score: d.recovery_score ?? null,
        strain: d.strain ?? null,
      }))}
    />
  );
}
