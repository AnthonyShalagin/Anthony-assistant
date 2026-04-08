# Skill: Strong CSV Parser

## Trigger
When a user uploads a .csv file via Telegram.

## Description
Parse workout exports from the Strong app. Computes set volume and
estimated 1-rep max (1RM) using the Epley formula, then stores all
data in the SQLite database.

## Expected CSV Columns
- Date, Workout Name, Exercise Name, Set Order, Weight, Reps

## Calculations
- **Volume**: weight × reps (per set)
- **Estimated 1RM** (Epley formula): weight × (1 + reps / 30)
  - If reps = 1, 1RM = weight (actual single)
  - If weight or reps ≤ 0, returns 0

## Storage
All sets stored in the `workouts` table using UPSERT
(unique on date + workout_name + exercise + set_order).
Safe to re-upload the same file.

## Response
After parsing, sends a Telegram summary with:
- Number of sets, exercises, and workout sessions
- List of exercises imported
