# Jarvis ↔ Dashboard integration

The dashboard's Supabase DB is the single source of truth. Jarvis can read
from it via `dashboard/ingestion/dashboard_query.py`.

## What to add to `jarvis/tools.py`

1. Add to imports at top:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard" / "ingestion"))
from dashboard_query import latest_metrics, metrics_range, goal_progress, recent_prs, latest_bloodwork
```

2. Append to `TOOL_SCHEMAS`:

```python
{
    "type": "function",
    "function": {
        "name": "dashboard_metrics",
        "description": "Query Anthony's daily health metrics (HRV, RHR, sleep, steps, recovery, strain). Use 'today' for the latest day or 'range' for the last N days.",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "enum": ["today", "range"]},
                "days": {"type": "integer", "description": "Used when scope=range. Default 7."},
            },
            "required": ["scope"],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "dashboard_goals",
        "description": "Check progress on Anthony's active health goals (steps, sleep, body fat).",
        "parameters": {"type": "object", "properties": {}},
    },
},
{
    "type": "function",
    "function": {
        "name": "dashboard_strength_prs",
        "description": "Recent personal records by exercise (best estimated 1RM in the last N weeks).",
        "parameters": {
            "type": "object",
            "properties": {"weeks": {"type": "integer", "default": 8}},
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "dashboard_bloodwork",
        "description": "Anthony's most recent bloodwork panel + biomarkers (A1C, ApoB, LDL, HDL, etc.).",
        "parameters": {"type": "object", "properties": {}},
    },
},
```

3. Add branches in `call_tool()`:

```python
if name == "dashboard_metrics":
    if args.get("scope") == "today":
        return {"ok": True, "data": latest_metrics()}
    return {"ok": True, "data": metrics_range(args.get("days", 7))}

if name == "dashboard_goals":
    return {"ok": True, "data": goal_progress()}

if name == "dashboard_strength_prs":
    return {"ok": True, "data": recent_prs(args.get("weeks", 8))}

if name == "dashboard_bloodwork":
    return {"ok": True, "data": latest_bloodwork()}
```

4. Add the env vars to `jarvis/.env`:

```
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

`dashboard_query.py` re-uses `db.py` from `dashboard/ingestion/`, so the
service-role key is required (it bypasses RLS).
