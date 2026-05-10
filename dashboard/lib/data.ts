// Server-side data fetchers. Each one falls back to mock data when the
// table is empty (or the Supabase env isn't configured) so the UI keeps
// rendering during incremental wiring.

import { admin } from "@/lib/supabase/admin";
import {
  getBloodwork as mockBloodwork,
  getDailyMetrics as mockDailyMetrics,
  getInBodyScans as mockInBody,
  getSleepDetails as mockSleep,
  getStrongSets as mockStrong,
  type BloodMarker,
  type DailyMetric,
  type InBodyScan,
  type SleepDetail,
  type StrongSet,
} from "@/lib/mock";

function configured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY
  );
}

export async function fetchDailyMetrics(days: number): Promise<DailyMetric[]> {
  if (!configured()) return mockDailyMetrics(days);
  try {
    const sb = admin();
    const { data, error } = await sb
      .from("daily_metrics")
      .select("date,hrv,rhr,sleep_score,sleep_hours,steps,recovery_score,strain")
      .order("date", { ascending: false })
      .limit(days);
    if (error || !data || data.length === 0) return mockDailyMetrics(days);
    return (data as DailyMetric[]).slice().reverse();
  } catch {
    return mockDailyMetrics(days);
  }
}

export async function fetchSleepDetails(days: number): Promise<SleepDetail[]> {
  if (!configured()) return mockSleep(days);
  try {
    const sb = admin();
    const { data, error } = await sb
      .from("sleep_detail")
      .select("date,deep_min,rem_min,light_min,awake_min,efficiency")
      .order("date", { ascending: false })
      .limit(days);
    if (error || !data || data.length === 0) return mockSleep(days);
    return (data as SleepDetail[]).slice().reverse();
  } catch {
    return mockSleep(days);
  }
}

export async function fetchInBody(): Promise<InBodyScan[]> {
  if (!configured()) return mockInBody();
  try {
    const sb = admin();
    const { data, error } = await sb
      .from("inbody_scans")
      .select("date,weight_lbs,bf_pct,skeletal_muscle_lbs")
      .order("date", { ascending: true });
    if (error || !data || data.length === 0) return mockInBody();
    return data as InBodyScan[];
  } catch {
    return mockInBody();
  }
}

export async function fetchStrongSets(weeks: number): Promise<StrongSet[]> {
  if (!configured()) return mockStrong(weeks);
  try {
    const sb = admin();
    // Supabase REST caps responses at 1000 rows; without a date filter we
    // were getting the OLDEST 1000 sets. Bound by date and return desc.
    const since = new Date();
    since.setUTCDate(since.getUTCDate() - weeks * 7);
    const sinceStr = since.toISOString().slice(0, 10);
    const { data, error } = await sb
      .from("workouts_strong")
      .select("date,exercise,set_number,reps,weight_lbs,e1rm,muscle_group")
      .gte("date", sinceStr)
      .order("date", { ascending: false })
      .limit(5000);
    if (error || !data || data.length === 0) return mockStrong(weeks);
    return (data as StrongSet[]).slice().reverse();
  } catch {
    return mockStrong(weeks);
  }
}

/** Latest single workout (for the "Last lift" chip on Today). */
export async function fetchLastWorkout(): Promise<{
  date: string;
  exercise: string;
  workout_name: string | null;
} | null> {
  if (!configured()) return null;
  try {
    const sb = admin();
    const { data, error } = await sb
      .from("workouts_strong")
      .select("date,exercise,workout_name")
      .order("date", { ascending: false })
      .limit(1);
    if (error || !data || data.length === 0) return null;
    return data[0] as { date: string; exercise: string; workout_name: string | null };
  } catch {
    return null;
  }
}

export type BloodPanel = {
  panel_date: string;
  lab_name: string | null;
  markers: BloodMarker[];
};

export async function fetchBloodwork(): Promise<BloodMarker[]> {
  if (!configured()) return mockBloodwork();
  try {
    const sb = admin();
    const panelsRes = await sb
      .from("bloodwork_panels")
      .select("id,panel_date,lab_name")
      .order("panel_date", { ascending: true });
    const panels = (panelsRes.data ?? []) as { id: string; panel_date: string; lab_name: string | null }[];
    if (panelsRes.error || panels.length === 0) return mockBloodwork();

    const ids = panels.map((p) => p.id);
    const markersRes = await sb
      .from("bloodwork_markers")
      .select("panel_id,marker,value,unit,ref_low,ref_high,status,category");
    type RawMarker = {
      panel_id: string;
      marker: string;
      value: number | string;
      unit: string | null;
      ref_low: number | null;
      ref_high: number | null;
      status: BloodMarker["status"];
      category: string | null;
    };
    const markers = (markersRes.data ?? []) as RawMarker[];
    if (markersRes.error) return mockBloodwork();

    const panelDateById = new Map(panels.map((p) => [p.id, p.panel_date]));

    return markers
      .filter((m) => ids.includes(m.panel_id))
      .map<BloodMarker>((m) => ({
        panel_date: panelDateById.get(m.panel_id) as string,
        marker: m.marker,
        value: Number(m.value),
        unit: m.unit ?? "",
        ref_low: m.ref_low,
        ref_high: m.ref_high,
        status: m.status,
        category: m.category ?? "Other",
      }));
  } catch {
    return mockBloodwork();
  }
}
