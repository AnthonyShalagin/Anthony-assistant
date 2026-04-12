# CLAUDE.md — Anthony Assistant

Guidance for future Claude Code sessions working on this repo.

---

## Project Overview

Personal assistant running on a DigitalOcean VPS. Four Telegram bots:

| Bot | Purpose | Brain |
|---|---|---|
| **Jarvis** (Alfred) | Master orchestrator across all domains | Claude Sonnet via OpenRouter + function calling |
| **Home Control** | SmartRent thermostat, Yale lock, sensors | Claude + function calling (scoped to home) |
| **Genesis Remote** | GV70 remote start/lock via bluelinky | Regex → *should migrate to LLM* |
| **Health Coach** | Oura, Whoop, Strong CSV briefings | Claude for Q&A, cron for briefings |

Supporting services:
- **Genesis Node.js service** (`genesis-bot/genesis-service/`) — runs bluelinky locally on port 3100
- All bots run as systemd services on Ubuntu 24.04 at `/root/Anthony-assistant/`

Domains:
- **Car**: Genesis GV70 (bluelinky, `brand: "hyundai"`)
- **Home**: SmartRent platform (Honeywell thermostat + Yale lock + leak sensors)
- **Health**: Oura (bearer token), Whoop (OAuth2, **API v2 not v1**), Strong app CSV uploads

---

## Critical Lessons Learned

### 1. Use LLM + function calling from day one for user-facing bots
Regex pattern matching fails miserably on natural language. Early bots used regex (`re.search(...)`) to parse commands like "set temp to 68 every night at 10pm". This worked for exact patterns but fell apart on variations like:
- "okay and also set 72F warm at 8am on weekdays, 9am on weekends"
- "set 72F heat on weekdays 8am, 9am on weekends"

The LLM-based approach (Claude via OpenRouter with `tools` parameter) handles these effortlessly. **Every bot should be LLM-powered from the start.** The pattern is in `jarvis/bot.py` and `home-bot/bot.py`:
- Tool schemas (`TOOLS` list) describe each action
- Tool handlers (`TOOL_HANDLERS` dict) map names to functions
- Tool-calling loop runs until LLM returns text (no more tool_calls)
- Keep `max_tokens=600-800`, `temperature=0.3`

### 2. Python `from config import X` collisions when reusing modules
When Jarvis imported sibling bot modules (`schedules.py`, `smart_home.py`, etc.), they did `from config import DB_PATH` — which Python resolved to **Jarvis's** `config.py` because Python caches modules by name (`sys.modules['config']`). The first `config` module imported wins for the whole process.

**Fix pattern:** Each shared module should either:
- Load its own `.env` explicitly via `load_dotenv(Path(__file__).parent / ".env")` and read `os.environ` directly
- Use a self-resolving path: `DB_PATH = str(Path(__file__).resolve().parent / "data" / "x.db")`

**Don't** rely on `from config import X` if the module will be imported from multiple parent processes.

### 3. Whoop API v1 is deprecated — use v2
`https://api.prod.whoop.com/developer/v1/recovery` returns 404. v2 works:
- `https://api.prod.whoop.com/developer/v2/recovery`
- `https://api.prod.whoop.com/developer/v2/cycle`
- `https://api.prod.whoop.com/developer/v2/activity/sleep`

OAuth scopes: `read:recovery`, `read:cycles`, `read:sleep`, `read:profile`.

### 4. Whoop OAuth requires client credentials in request body, not Basic Auth
`requests-oauthlib` defaults to HTTP Basic Auth for token endpoints. Whoop rejects this with `invalid_client`. Must pass `include_client_id=True` to `fetch_token()` and manually handle refresh via `requests.post` with credentials in the body (see `health-agent/clients/whoop.py`).

### 5. Oura dates sleep to the night it started, not the morning after
If the user wakes up on April 11, the Oura sleep score for that sleep is dated April 10. Always check both today and yesterday when displaying "today's" sleep metrics.

### 6. bluelinky uses `brand: "hyundai"` for Genesis
Counterintuitively, Genesis vehicles are handled through the Hyundai platform in bluelinky. `brand: "genesis"` throws "Constructor genesis is not managed". Also: `require("bluelinky").default || require("bluelinky")` to handle CommonJS/ESM dual export.

### 7. Vercel functions are stateless — don't use for long-running auth sessions
Original Genesis remote was on Vercel, but bluelinky caches auth in memory. Cold starts forced re-login every time, hitting 30s timeouts. Solution: run bluelinky as a persistent Node.js service on the DO server at `127.0.0.1:3100`.

### 8. Telegram long-polling: only one process at a time
Telegram's `getUpdates` returns a **409 Conflict** if two processes poll the same bot. When debugging, always `systemctl stop <bot>` before running manual test scripts.

### 9. Strong CSV gotchas
- **Tab-delimited**, not comma-separated. Auto-detect with `_detect_delimiter()`.
- **Floats for integer fields** — `Reps` is `"12.0"` not `"12"`. Use `int(float(x))`.
- **Warmup sets** have `Set Order = "W"`, not a number. Treat as `set_order = 0`.
- **Quoted strings** in some fields (e.g. `"Afternoon Workout"`).

### 10. Keep briefings short and non-obvious
Users don't want restated metrics (they can see those in their apps). LLM prompt should emphasize:
- Non-obvious correlations (e.g. HRV drops after back-to-back training)
- Missed patterns (e.g. neglected muscle groups)
- "Nothing flagged" is a valid response

See `health-agent/briefing/generator.py` for the functional-medicine-practitioner prompt.

### 11. Wearable data syncs lazily
Oura and Whoop data is only available after the user's phone syncs with their wearable. If the API returns no data, it usually means the app hasn't opened yet. Schedule pulls after 9 AM to give users time to manually sync.

### 12. Security: authorization whitelist from the start
Every bot must enforce `ALLOWED_CHAT_IDS` (comma-separated list in `.env`). Silently ignore unauthorized messages. See `*/auth.py` in each bot.

### 13. `.env` discipline
- **Never** commit `.env` files. Add to `.gitignore` immediately.
- **Never** put real credentials in `.env.example`.
- Prefer `load_dotenv(Path(__file__).parent / ".env")` over global env vars.

---

## Architecture Patterns

### LLM tool-calling loop (canonical implementation)
```python
for _ in range(5):  # max rounds
    response = _llm_call(messages)  # with tools parameter
    msg = response["choices"][0]["message"]
    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        send_text(msg["content"])
        break
    # Execute tools
    messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
    for tc in tool_calls:
        result = call_tool(tc["function"]["name"], json.loads(tc["function"]["arguments"]))
        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result)})
```

### Per-user conversation history
```python
_history: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY_TURNS = 6  # Trim aggressively
```
Trim by counting user messages, keep last N turns.

### Async SmartRent from sync bot
`smartrent-py` is async-only. Use a helper:
```python
def run_async(coro):
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result(timeout=30)
```

---

## Deployment Checklist for New Bot

1. Create directory: `mkdir new-bot`
2. Files needed:
   - `bot.py` — LLM-powered handler (copy pattern from `home-bot/bot.py`)
   - `auth.py` — chat ID whitelist (copy from any bot)
   - `.env` (gitignored) with `TELEGRAM_BOT_TOKEN`, `ALLOWED_CHAT_IDS`, `OPENROUTER_API_KEY`
   - `.env.example` with placeholders only
   - `.gitignore` including `.env`, `.venv/`, `data/`
   - `requirements.txt`
3. Create bot via @BotFather, add token to `.env`.
4. On server:
   ```bash
   cd ~/Anthony-assistant/new-bot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
5. Systemd service at `/etc/systemd/system/new-bot.service`:
   ```ini
   [Unit]
   Description=New Bot
   After=network.target
   [Service]
   Type=simple
   WorkingDirectory=/root/Anthony-assistant/new-bot
   ExecStart=/root/Anthony-assistant/new-bot/.venv/bin/python bot.py
   Restart=always
   RestartSec=10
   [Install]
   WantedBy=multi-user.target
   ```
6. `systemctl daemon-reload && systemctl enable new-bot && systemctl start new-bot`

---

## Known Issues / TODO

- [ ] genesis-bot still uses regex — migrate to LLM pattern like home-bot
- [ ] Emma's chat ID (`9082279594`) may actually be a phone number; verify once she texts
- [ ] Whoop developer app verification may unlock additional endpoints
- [ ] No persistent conversation memory across restarts (in-memory only)
- [ ] No rate limiting on LLM calls (could rack up OpenRouter costs if abused)

---

## Secret Rotation Checklist

These credentials appeared in chat transcripts and should be rotated periodically:
- SmartRent password
- Genesis account password
- All Telegram bot tokens
- OpenRouter API key
- Oura personal access token
- Whoop client secret
