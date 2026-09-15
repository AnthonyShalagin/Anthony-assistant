# CLAUDE.md — Hermes Health Agent

## Project Overview

Personal health intelligence agent built on Hermes Agent (by Nous Research) that:

- Pulls daily data from Oura Ring and Whoop APIs
- Accepts Strong app CSV uploads via Telegram
- Stores everything in SQLite
- Generates health briefings on demand (via Jarvis); the weekly summary lives in the Life OS review
- Runs on a VPS in a security-hardened Docker container

GitHub base: <https://github.com/NousResearch/hermes-agent>

---

## User Preferences (IMPORTANT)

- **Telegram briefings must NOT analyze Strong workout logs.** The user does
  not log every workout in the Strong app, so a gap in the log is not a real
  signal of skipped training. Anchor analysis on **Whoop strain** + **Oura
  activity** instead — Whoop strain captures actual training load
  automatically. Briefing prompts (`briefing/generator.py`) and any future
  Telegram-facing analysis tooling must follow this rule.
- Strong CSV uploads are still ingested for the dashboard / portfolio history
  — just don't surface them in Telegram analysis.
- **Garmin is removed from automated ingestion** (no Garmin client, no schedule
  entry, no env vars) and any Garmin signals are out of scope for analysis.
  The user syncs Garmin sporadically, so the data isn't reliable as a daily
  signal. Same rule as Strong: even if Garmin data ever appears in the DB,
  prompts must not draw judgments from it.

## What's Built (All Phases Complete)

73 tests passing. All code lives in `health-agent/`.

### Architecture

```
health-agent/
├── config.py                 # Env var configuration
├── database.py               # SQLite layer (3 tables, UPSERT)
├── main.py                   # Entry point: scheduler + Telegram bot
├── scheduler.py              # Cron-like job scheduler (Eastern Time)
├── healthcheck.py            # 6:00 AM pre-pull verification
├── telegram_bot.py           # Long-polling bot for messages + CSV uploads
├── clients/
│   ├── oura.py               # Oura Ring API (bearer token)
│   └── whoop.py              # Whoop API (OAuth2 + auto-refresh)
├── parsers/
│   └── strong.py             # Strong app CSV parser (Epley 1RM)
├── briefing/
│   ├── trends.py             # 7d/30d averages, trend arrows (↑↓→)
│   └── generator.py          # LLM briefing via OpenRouter/Claude
├── skills/                   # Hermes Agent SKILL.md definitions
│   ├── SKILL_oura_pull.md
│   ├── SKILL_whoop_pull.md
│   ├── SKILL_strong_parser.md
│   └── SKILL_health_briefing.md
├── tests/                    # 73 tests across all modules
├── Dockerfile                # python:3.11-slim, non-root, read-only
├── docker-compose.yml        # Security-hardened deployment
├── requirements.txt          # requests, requests-oauthlib, pandas
└── .env.example              # Environment variable template
```

---

## Database Schema (SQLite)

### health_metrics
| Column      | Type    | Notes                                    |
|-------------|---------|------------------------------------------|
| date        | TEXT    | ISO format (YYYY-MM-DD)                  |
| source      | TEXT    | "oura", "whoop"                          |
| metric_name | TEXT    | e.g. "sleep_score", "hrv_rmssd"          |
| value       | REAL    | Nullable for missing data                |
| unit        | TEXT    | "score", "ms", "bpm", "%", etc.          |
| recorded_at | TEXT    | Auto-set on insert/update                |

**UNIQUE** on `(date, source, metric_name)` — UPSERT safe.

### workouts
| Column        | Type    | Notes                              |
|---------------|---------|-------------------------------------|
| date          | TEXT    | ISO format                         |
| workout_name  | TEXT    | e.g. "Push Day"                    |
| exercise      | TEXT    | e.g. "Bench Press"                 |
| set_order     | INTEGER | Set number within the exercise     |
| weight        | REAL    | In user's configured unit          |
| reps          | INTEGER |                                     |
| volume        | REAL    | weight × reps                      |
| estimated_1rm | REAL    | Epley formula: w × (1 + r/30)      |

**UNIQUE** on `(date, workout_name, exercise, set_order)` — UPSERT safe.

### oauth_tokens
| Column        | Type | Notes                                   |
|---------------|------|-----------------------------------------|
| provider      | TEXT | "whoop" (UNIQUE)                        |
| access_token  | TEXT |                                          |
| refresh_token | TEXT | Preserved on upsert if new value is NULL |
| token_type    | TEXT | Default "Bearer"                        |
| expires_at    | TEXT | ISO timestamp                           |
| extra         | TEXT | JSON blob (provider-specific extras)    |

---

## API Details

### Oura Ring
- **Auth**: Bearer token (`OURA_TOKEN`)
- **Base URL**: `https://api.ouraring.com/v2/usercollection`
- **Endpoints**: `daily_sleep`, `daily_readiness`, `daily_activity`, `daily_hrv`, `workout`
- **Metrics**: sleep_score, readiness_score, activity_score, hrv_average, steps, active_calories, heart_rate_average, breath_average, temperature_deviation, workout_count, workout_minutes, strength_sessions, strength_minutes
- **Workouts**: Anthony logs lifting only in Strong. Strong writes to Apple Health and Oura imports it, so `workout` is how training shows up without CSV exports. Each pull writes yesterday and today, zeros included.
- **Token caveat**: Oura stopped issuing personal access tokens in Dec 2025. Older tokens may keep working; if pulls start returning 401, move to Oura OAuth2.

### Whoop
- **Auth**: OAuth2 with the `offline` scope, so a refresh token is issued
- **Base URL**: `https://api.prod.whoop.com/developer/v2`
- **Endpoints**: `recovery`, `cycle`, `activity/sleep`
- **Metrics**: recovery_score, resting_heart_rate, hrv_rmssd, spo2, skin_temp, strain_score, kilojoules, avg_heart_rate, sleep_performance, sleep_consistency, sleep_efficiency
- **Token refresh**: manual in `_get_session`, 5 minutes before expiry, sending `scope=offline`. Whoop rotates refresh tokens (each refresh kills the previous one), so refreshes are serialized with a file lock next to the DB. Both the scheduler and Jarvis must point at the same DB, or they will invalidate each other's tokens.

### Strong App
- **Input**: CSV file uploaded via Telegram (optional, only for set-level detail; session counts come from Oura)
- **Expected columns**: Date, Workout Name, Exercise Name, Set Order, Weight, Reps
- **Calculations**: Volume (weight × reps), Estimated 1RM (Epley: weight × (1 + reps/30))

---

## Cron Schedule (Eastern Time)

| Time          | Job              | Description                       |
|---------------|------------------|-----------------------------------|
| 09:00 daily   | Healthcheck      | DB + API token verification (silent) |
| 09:30 daily   | Oura Pull        | Sleep, readiness, activity, HRV, workouts |
| 09:35 daily   | Whoop Pull       | Recovery, strain, sleep            |
| 09:40 daily   | Supabase Sync    | Push last 7 days to the dashboard  |

No scheduled Telegram messages. Health is one section of the Sunday Life OS
review on Anthony's Mac, which reads this DB over ssh with `export_week.py`
(stdlib, read-only). Briefings are still available on demand through Jarvis.

---

## LLM Briefing

- **Provider**: OpenRouter (`OPENROUTER_API_KEY`)
- **Default model**: `anthropic/claude-sonnet-4-6`
- **Daily prompt**: Identify top trend, flag concerns, one recommendation, <200 words
- **Weekly prompt**: Week summary, compare vs 30-day baseline, 2-3 recommendations, <400 words
- **Missing data**: Shows "—", LLM is told which sources are missing
- **Trend arrows**: ↑ (≥5% above 30d avg), ↓ (≥5% below), → (stable)

---

## Docker Deployment

```yaml
# Security hardening:
read_only: true           # Read-only filesystem
cap_drop: [ALL]           # Drop all Linux capabilities
no-new-privileges: true   # Prevent privilege escalation
tmpfs: /tmp               # Writable temp only
# No exposed ports — Telegram polls outbound only
```

Image: `python:3.11-slim`, runs as non-root user `agent`.

---

## Environment Variables

| Variable              | Required | Description                          |
|-----------------------|----------|--------------------------------------|
| TELEGRAM_BOT_TOKEN    | Yes      | Telegram bot token from @BotFather   |
| TELEGRAM_CHAT_ID      | Yes      | Your Telegram chat ID                |
| OURA_TOKEN            | Yes      | Oura personal access token           |
| WHOOP_CLIENT_ID       | Yes      | Whoop OAuth2 client ID               |
| WHOOP_CLIENT_SECRET   | Yes      | Whoop OAuth2 client secret           |
| OPENROUTER_API_KEY    | Yes      | OpenRouter API key for LLM           |
| LLM_MODEL             | No       | Default: anthropic/claude-sonnet-4-6 |
| DB_PATH               | No       | Default: health-agent/data/health.db |

---

## Test Coverage

73 tests across 9 test files:

| File                  | Tests | Covers                                    |
|-----------------------|-------|-------------------------------------------|
| test_database.py      | 12    | Schema, CRUD, UPSERT, averages, queries   |
| test_strong_parser.py | 12    | Epley 1RM, volume, CSV parsing, idempotency|
| test_trends.py        | 12    | Trend arrows, formatting, trend blocks     |
| test_briefing.py      | 8     | Context building, LLM calls, full briefing |
| test_telegram.py      | 7     | Send, split, download, CSV upload handling |
| test_scheduler.py     | 7     | Cron matching, day-of-week, double-run     |
| test_oura.py          | 4     | Pull daily, error handling, token verify   |
| test_whoop.py         | 2     | Pull daily with mock OAuth, no-token case  |
| test_healthcheck.py   | 4     | DB check, full healthcheck, partial fail   |

Run tests: `cd health-agent && python -m pytest tests/ -v`

---

## Security Checklist

- [x] Non-root Docker user
- [x] Read-only filesystem
- [x] All capabilities dropped
- [x] No exposed ports (outbound Telegram polling only)
- [x] Secrets via environment variables (never hardcoded)
- [x] .env in .gitignore
- [x] No dangerous Hermes Agent tools (execute_code, browser, computer disabled)
- [x] UPSERT prevents data corruption on re-runs
- [x] OAuth tokens stored encrypted-at-rest in SQLite (provider-managed)
