# Anthony Dashboard

A Whoop-style personal health dashboard. Five tabs: **Today / Trends /
Strength / Bloodwork / Goals**.

## Stack

- **Next.js 16** (App Router, Turbopack) + **TypeScript** + **Tailwind v4**
- **Recharts** for visualizations, dark Whoop-style palette
- **Supabase** (Postgres + Auth) — single source of truth
- **Vercel** for hosting (free tier)

The data ingestion lives in `ingestion/` (Python). It runs on the same
DigitalOcean VPS as the Telegram bots and writes to the same Supabase DB
that the dashboard reads from. Jarvis can also query the dashboard data —
see `JARVIS_INTEGRATION.md`.

## Local dev

```bash
cd dashboard
npm install
cp .env.local.example .env.local   # fill in Supabase keys
npm run dev
```

Right now everything renders from `lib/mock.ts`. Once Supabase is up and
ingestion has run, swap server-component fetches in each `app/*/page.tsx`
to read from `lib/supabase/server.ts` instead of `mock`.

## Setup checklist

1. **Create the Supabase project** at https://supabase.com (free tier).
   - Save the project URL, anon key, and service-role key.
2. **Run the schema**: Studio → SQL Editor → paste `supabase/migrations/0001_init.sql` → Run.
3. **Configure auth**: Authentication → Providers → enable Google. Restrict by email in middleware.
4. **Set env vars**: copy `.env.local.example` → `.env.local`.
5. **Wire ingestion** on the VPS — see `ingestion/README.md`.
6. **Deploy** to Vercel with `dashboard/` as the root directory.

## Tabs

### Today
- Whoop-style recovery ring (green ≥67, amber 34-66, red <34)
- HRV / RHR / Sleep / Steps / Weight / Body Fat metric cards
- 7-day mini-trend strip
- Last-night sleep stage breakdown + 7-day stacked bars

### Trends
- 30-day charts: HRV, Resting HR, Sleep hours, Sleep score, Steps, Recovery score
- Period toggle (7d / 30d / 90d) — UI present, wiring pending

### Strength
- Personal-record cards for the top 4 lifts by e1RM
- Per-exercise weight-over-time (chip-selector)
- Estimated 1RM trend for big lifts (squat / bench / deadlift / OHP)
- Weekly volume per muscle group (stacked bar)

### Bloodwork
- Function-Health-style biomarker cards grouped by category
- Reference range bar with marker position
- vs-previous-panel delta
- "Upload Panel" button (stub)

### Goals
- Three cards: Steps (8k/day weekly avg), Sleep (7.5h/day weekly avg), Body Fat (≤15% monthly)
- 12-week history table with hit/miss
- Body-fat history with target line marked

## Visual language

- Background `#0a0a0a`, surface `#141414`, border `#262626`
- Recovery green `#00ff94`, strain blue `#0093ff`, sleep purple `#9b6dff`,
  alert red `#ff3860`, warn amber `#ffb020`
- Mono numerals (Geist Mono, tabular-nums) for everything quantitative

## What's mocked vs real

| Layer | Status |
|---|---|
| Visual design + all 5 tabs | ✅ Render with mock data |
| Supabase schema | ✅ SQL written, not yet applied |
| Supabase clients | ✅ Stubs in `lib/supabase/` |
| Ingestion (Oura/Whoop/Strong) | ✅ Stubs written, untested live |
| InBody paste form | ⏳ Pending |
| Bloodwork upload + parser | ⏳ Pending |
| Auth (Google OAuth) | ⏳ Middleware pending |
| Vercel deploy | ⏳ Pending |
| Jarvis tool wiring | ✅ Helper module + integration doc |

## Build

```bash
npm run build
```
