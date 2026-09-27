import { fetchBloodwork, fetchDailyMetrics, fetchInBody, fetchStrongSets } from "@/lib/data";
import { TodayClient } from "./today-client";

export const dynamic = "force-dynamic";

export default async function TodayPage() {
  const [days, inbody, sets, markers] = await Promise.all([
    fetchDailyMetrics(60),
    fetchInBody(),
    fetchStrongSets(8),
    fetchBloodwork(),
  ]);

  // One lifting session per day with logged sets
  const sessionDates = [...new Set(sets.map((s) => s.date))].sort();

  return (
    <TodayClient
      metrics={days.map((d) => ({
        date: d.date,
        hrv: d.hrv ?? null,
        rhr: d.rhr ?? null,
        sleep_hours: d.sleep_hours ?? null,
        steps: d.steps ?? null,
        recovery_score: d.recovery_score ?? null,
        strain: d.strain ?? null,
      }))}
      inbody={inbody}
      sessionDates={sessionDates}
      markers={markers}
    />
  );
}
