-- Split wearable sources into separate columns so Oura and Whoop can both
-- be visible at the same time. Convention going forward:
--   hrv, rhr, sleep_score, sleep_hours, steps  → Oura (preferred)
--   hrv_whoop, rhr_whoop, sleep_score_whoop, sleep_hours_whoop → Whoop
--   recovery_score, strain → Whoop only (Oura has no equivalent)

alter table daily_metrics
  add column if not exists hrv_whoop numeric,
  add column if not exists rhr_whoop numeric,
  add column if not exists sleep_score_whoop smallint,
  add column if not exists sleep_hours_whoop numeric;
