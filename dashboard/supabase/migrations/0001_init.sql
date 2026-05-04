-- Anthony Health Dashboard — initial schema.
-- Apply via: Supabase Studio → SQL editor → paste + run.

create extension if not exists "uuid-ossp";

-- ---------- Daily metrics (Oura + Whoop merged by date) ----------
create table if not exists daily_metrics (
  date date primary key,
  hrv numeric,                  -- ms
  rhr numeric,                  -- bpm
  sleep_score smallint,         -- 0-100
  sleep_hours numeric,
  steps integer,
  recovery_score smallint,      -- Whoop 0-100
  strain numeric,               -- Whoop 0-21
  source text,                  -- "oura" | "whoop" | "merged"
  raw jsonb,                    -- raw payload for debugging
  updated_at timestamptz default now()
);

create index if not exists daily_metrics_updated_idx on daily_metrics (updated_at desc);

-- ---------- Sleep stages (per night) ----------
create table if not exists sleep_detail (
  date date primary key references daily_metrics(date) on delete cascade,
  deep_min smallint,
  rem_min smallint,
  light_min smallint,
  awake_min smallint,
  efficiency smallint,           -- 0-100
  bedtime timestamptz,
  wake_time timestamptz,
  raw jsonb,
  updated_at timestamptz default now()
);

-- ---------- Strong app workouts ----------
create table if not exists workouts_strong (
  id uuid primary key default uuid_generate_v4(),
  date date not null,
  workout_name text,
  exercise text not null,
  set_number smallint not null,
  reps smallint,
  weight_lbs numeric,
  e1rm numeric,                  -- Epley estimated 1RM
  muscle_group text,
  notes text,
  imported_at timestamptz default now(),
  unique (date, exercise, set_number, reps, weight_lbs)
);

create index if not exists workouts_strong_date_idx on workouts_strong (date desc);
create index if not exists workouts_strong_exercise_idx on workouts_strong (exercise);

-- ---------- InBody scans (Lifetime) ----------
create table if not exists inbody_scans (
  date date primary key,
  weight_lbs numeric,
  bf_pct numeric,
  skeletal_muscle_lbs numeric,
  raw_paste text,                -- preserve original paste
  notes text,
  imported_at timestamptz default now()
);

-- ---------- Bloodwork ----------
create table if not exists bloodwork_panels (
  id uuid primary key default uuid_generate_v4(),
  panel_date date not null,
  lab_name text,                 -- "Function Health", "Quest", etc.
  source_file text,
  notes text,
  imported_at timestamptz default now()
);

create table if not exists bloodwork_markers (
  id uuid primary key default uuid_generate_v4(),
  panel_id uuid references bloodwork_panels(id) on delete cascade,
  marker text not null,          -- "A1C", "ApoB", etc.
  value numeric not null,
  unit text,
  ref_low numeric,
  ref_high numeric,
  status text,                   -- "optimal" | "normal" | "high" | "low"
  category text                  -- "Heart" | "Metabolic" | "Hormones" | ...
);

create index if not exists bloodwork_markers_panel_idx on bloodwork_markers (panel_id);
create index if not exists bloodwork_markers_marker_idx on bloodwork_markers (marker);

-- ---------- Goals ----------
create table if not exists goals (
  id uuid primary key default uuid_generate_v4(),
  metric text not null,          -- "steps" | "sleep" | "bf"
  label text not null,
  target numeric not null,
  unit text,
  period text not null,          -- "weekly" | "monthly"
  comparison text not null default 'gte',  -- "gte" | "lte"
  active boolean default true,
  created_at timestamptz default now()
);

insert into goals (metric, label, target, unit, period, comparison) values
  ('steps', 'Steps',     8000,  '/day avg', 'weekly',  'gte'),
  ('sleep', 'Sleep',     7.5,   'hr/day avg','weekly',  'gte'),
  ('bf',    'Body Fat',  15.0,  '%',        'monthly', 'lte')
on conflict do nothing;

-- ---------- Row-Level Security ----------
-- Single-user app: lock everything to authenticated requests.
alter table daily_metrics enable row level security;
alter table sleep_detail enable row level security;
alter table workouts_strong enable row level security;
alter table inbody_scans enable row level security;
alter table bloodwork_panels enable row level security;
alter table bloodwork_markers enable row level security;
alter table goals enable row level security;

-- Authenticated users (we'll restrict to one email at the auth layer) can read everything.
create policy "auth_read_daily_metrics" on daily_metrics for select using (auth.role() = 'authenticated');
create policy "auth_read_sleep_detail" on sleep_detail for select using (auth.role() = 'authenticated');
create policy "auth_read_workouts" on workouts_strong for select using (auth.role() = 'authenticated');
create policy "auth_read_inbody" on inbody_scans for select using (auth.role() = 'authenticated');
create policy "auth_read_panels" on bloodwork_panels for select using (auth.role() = 'authenticated');
create policy "auth_read_markers" on bloodwork_markers for select using (auth.role() = 'authenticated');
create policy "auth_read_goals" on goals for select using (auth.role() = 'authenticated');

-- Authenticated users can also write (single-user app). Service role bypasses RLS for ingestion.
create policy "auth_write_inbody" on inbody_scans for all using (auth.role() = 'authenticated');
create policy "auth_write_workouts" on workouts_strong for all using (auth.role() = 'authenticated');
create policy "auth_write_panels" on bloodwork_panels for all using (auth.role() = 'authenticated');
create policy "auth_write_markers" on bloodwork_markers for all using (auth.role() = 'authenticated');
create policy "auth_write_goals" on goals for all using (auth.role() = 'authenticated');
