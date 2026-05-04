# Skill: Health Briefing

## Schedule
- **Daily**: Every day at 07:30 AM Eastern
- **Weekly deep-dive**: Sundays at 09:00 AM Eastern

## Description
Generate an LLM-powered health briefing based on aggregated data from Oura
and Whoop. Delivers a formatted message via Telegram. Strong workouts and
Garmin data are NOT used for analysis — both have inconsistent sync
patterns and would lead the agent to draw bad conclusions from gaps.

## How It Works
1. Query 7-day and 30-day averages for all tracked metrics
2. Compute trend arrows: ↑ (improving ≥5%), ↓ (declining ≥5%), → (stable)
3. Gather recent workout summaries
4. Send structured context to LLM (OpenRouter / Claude)
5. Format and deliver via Telegram

## LLM Prompt Rules
- Identify the top trend (positive or negative)
- Flag concerns: declining HRV, overtraining signs, poor sleep
- Give ONE actionable recommendation (daily) or 2-3 (weekly)
- Under 200 words (daily) or 400 words (weekly)
- Do NOT repeat raw numbers — user sees those in the metrics block
- If a data source is missing, acknowledge briefly but don't speculate

## Missing Data
- Metrics show "—" when unavailable
- LLM is told which sources are missing so it doesn't hallucinate

## Tracked Metrics
| Source | Metrics |
|--------|---------|
| Oura   | Sleep Score, Readiness, Activity, HRV |
| Whoop  | Recovery, Strain, HRV (RMSSD), Sleep Performance |
