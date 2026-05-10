import { fetchDailyMetrics, fetchInBody, fetchLastWorkout } from "@/lib/data";
import { TodayClient } from "./today-client";

export const dynamic = "force-dynamic";

export default async function TodayPage() {
  const [days, inbody, lastWorkout] = await Promise.all([
    fetchDailyMetrics(400), // 400 days lets us compute 365d avg + prior 365d delta
    fetchInBody(),
    fetchLastWorkout(),
  ]);

  return (
    <TodayClient
      metrics={days.map((d) => ({
        date: d.date,
        hrv: d.hrv ?? null,
        rhr: d.rhr ?? null,
        sleep_score: d.sleep_score ?? null,
        sleep_hours: d.sleep_hours ?? null,
        steps: d.steps ?? null,
        recovery_score: d.recovery_score ?? null,
        strain: d.strain ?? null,
        source: null,
      }))}
      inbody={inbody}
      lastWorkout={lastWorkout}
    />
  );
}
