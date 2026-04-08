# Skill: Garmin Daily Pull

## Schedule
Every day at 07:10 AM Eastern

## Description
Pull daily health metrics from the Garmin Connect wellness API and store them in SQLite.
Uses OAuth 1.0a authentication.

## Metrics Collected
- Steps, active calories, total calories, distance
- Moderate and vigorous intensity minutes
- Body battery (high/low for the day)
- Stress levels (average and max)

## Authentication
OAuth 1.0a via `GARMIN_CONSUMER_KEY` and `GARMIN_CONSUMER_SECRET`.
Access tokens stored in `oauth_tokens` table with the resource owner secret in the `extra` JSON field.

## API
- Base: `https://apis.garmin.com/wellness-api/rest`
- Endpoints: `dailies`, `bodyBattery`, `stressDetails`

## Error Handling
- If authentication fails, report via Telegram.
- Individual endpoint failures don't block other metrics.

## Storage
All metrics stored via UPSERT in `health_metrics` table.
