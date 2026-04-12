# CLAUDE.md — Anthony Assistant

Guidance for future Claude Code sessions working on this repo.

## What this is

Personal assistant running on a DigitalOcean VPS. A set of domain-specific
Telegram bots (car, home, health) plus a master orchestrator (Jarvis/Alfred)
that routes across them. Each bot is LLM-powered with function calling —
no regex for natural language.

Layout:
- `jarvis/` — master bot, all tools
- `home-bot/` — SmartRent (thermostat, lock, sensors)
- `genesis-bot/` — Genesis GV70 (has a Node.js bluelinky sidecar)
- `health-agent/` — Oura, Whoop, Strong CSV

Each bot runs as its own systemd service on the VPS.

## Principles

- **LLM + function calling for anything user-facing.** Don't write regex
  parsers for natural language. Define tools, let the model call them.
- **Each bot owns its config.** Load `.env` relative to its own directory.
  Shared modules must not assume a particular `config.py` — Python caches
  module names globally, so shared-name collisions will burn you.
- **Authorization whitelist on every bot from day one.** No exceptions.
- **Secrets never touch git.** `.env` is gitignored everywhere;
  `.env.example` has placeholders only; audit before commits.
- **Prefer persistent services over stateless platforms** when the
  integration needs long-lived auth (e.g. bluelinky → local Node service,
  not Vercel).
- **Keep user-facing output short.** Don't restate data they can see in
  their own apps. Surface patterns, not numbers.

## Working on this repo

- Develop on a feature branch, commit on every meaningful change, push
  before asking the user to deploy.
- Deployment is `git pull && systemctl restart <service>` on the VPS.
- When adding a bot, copy the pattern from `home-bot/bot.py` (LLM loop,
  tool schemas, whitelist, history trimming).
- When debugging, remember Telegram long-polling is exclusive — stop the
  service before running manual probes against the same bot token.

## Gotchas to remember

- Third-party APIs drift — check current docs before assuming endpoints
  (we've already been bitten by Whoop v1 → v2).
- Wearable data is lazy — the device API only returns what the user's
  phone has synced. Schedule pulls late enough that sync has happened.
- CSV exports from consumer apps are messy — expect inconsistent
  delimiters, float-vs-int mismatches, quoted fields, and special tokens.
- OAuth libraries default to HTTP Basic Auth for token endpoints; many
  APIs want credentials in the body instead. Check the provider's docs.

## Maintenance

- Rotate credentials periodically (bot tokens, API keys, passwords).
- When the user mentions credentials in chat, treat them as compromised
  once the session ends and flag for rotation.
- Keep `CLAUDE.md` high-level. Put implementation details in code comments
  or in the relevant bot's own README.
