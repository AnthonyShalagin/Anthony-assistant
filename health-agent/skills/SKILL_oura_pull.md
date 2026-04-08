# Skill: Oura Daily Pull

## Schedule
Every day at 07:00 AM Eastern

## Description
Pull daily health metrics from the Oura Ring API and store them in the local SQLite database.

## Metrics Collected
- Sleep score and sub-scores (efficiency, latency, restfulness)
- Readiness score and contributors (activity balance, body temperature, HRV balance, recovery index, resting heart rate, sleep balance)
- Activity score (active calories, steps, walking distance)
- HRV average, heart rate average, breathing rate

## Authentication
Bearer token via `OURA_TOKEN` environment variable.
Token obtained from https://cloud.ouraring.com/personal-access-tokens

## API
- Base: `https://api.ouraring.com/v2/usercollection`
- Endpoints: `daily_sleep`, `daily_readiness`, `daily_activity`, `daily_hrv`

## Error Handling
- If the API returns an error, log it and continue with other metric types.
- Missing data is stored as NULL — never fabricate values.

## Storage
All metrics are stored in the `health_metrics` table using UPSERT (safe to re-run).
