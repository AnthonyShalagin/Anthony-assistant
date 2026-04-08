# Skill: Whoop Daily Pull

## Schedule
Every day at 07:05 AM Eastern

## Description
Pull daily health metrics from the Whoop API and store them in the local SQLite database.
Handles OAuth2 token refresh automatically.

## Metrics Collected
- Recovery score, resting heart rate, HRV (RMSSD), SpO2, skin temperature
- Strain score, kilojoules burned, average heart rate
- Sleep performance %, sleep consistency %, sleep efficiency %

## Authentication
OAuth2 with automatic token refresh.
- Credentials: `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`
- Tokens stored in `oauth_tokens` table, refreshed automatically when expired.

## API
- Base: `https://api.whoop.com/developer/v1`
- Endpoints: `recovery`, `cycle`, `activity/sleep`

## Error Handling
- If token refresh fails, report via Telegram and skip this pull.
- Individual metric fetch failures don't block other metrics.

## Storage
All metrics stored via UPSERT in `health_metrics` table.
OAuth tokens stored in `oauth_tokens` table.
