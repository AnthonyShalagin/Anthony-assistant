# Ingestion

These scripts pull from Oura/Whoop and write to Supabase. They run on the
DigitalOcean VPS as a daily cron, the same box as the existing bots.

## Layout

- `sync_oura.py` — pulls last N days of HRV/RHR/sleep/steps from Oura.
- `sync_whoop.py` — pulls recovery/strain/sleep from Whoop v2.
- `sync_strong.py` — parses a Strong CSV export (manual upload).
- `db.py` — Supabase client + upsert helpers.
- `backfill.py` — one-shot, pulls all available history (run once).
- `daily.sh` — wrapper invoked by cron.

## Setup on VPS

```bash
cd /opt/anthony-assistant/dashboard/ingestion
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OURA_TOKEN, WHOOP_*
```

Cron entry:

```
# 6am ET daily — wearables have synced by then
0 11 * * * cd /opt/anthony-assistant/dashboard/ingestion && ./daily.sh >> /var/log/dashboard-sync.log 2>&1
```

## First-run backfill

```bash
python backfill.py --days 9999
```

Pulls everything Oura/Whoop will give us, upserts into Supabase.
