"""Healthcheck — verifies DB accessibility and API token validity.

Runs at 6:00 AM before daily pulls. Reports status via Telegram.
"""

import logging
from typing import Optional

from config import OURA_TOKEN, DB_PATH
from database import get_db, init_db
from telegram_bot import send_message

logger = logging.getLogger(__name__)


def check_database(db_path: Optional[str] = None) -> tuple[bool, str]:
    """Verify the database is accessible and tables exist."""
    try:
        path = db_path or DB_PATH
        init_db(path)
        with get_db(path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {r["name"] for r in tables}
            required = {"health_metrics", "workouts", "oauth_tokens"}
            missing = required - table_names
            if missing:
                return False, f"Missing tables: {missing}"
            # Quick write test
            conn.execute(
                "INSERT OR IGNORE INTO health_metrics (date, source, metric_name, value) "
                "VALUES ('1970-01-01', '_healthcheck', '_test', 0)"
            )
            conn.execute(
                "DELETE FROM health_metrics WHERE source='_healthcheck'"
            )
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_oura_token(token: Optional[str] = None) -> tuple[bool, str]:
    """Verify Oura bearer token is valid."""
    from clients.oura import verify_token
    t = token or OURA_TOKEN
    if not t:
        return False, "OURA_TOKEN not configured"
    ok = verify_token(t)
    return ok, "OK" if ok else "Token invalid or expired"


def check_whoop_token(db_path: Optional[str] = None) -> tuple[bool, str]:
    """Verify Whoop OAuth token is valid (or can be refreshed)."""
    from clients.whoop import verify_token
    ok = verify_token(db_path)
    return ok, "OK" if ok else "Token invalid — may need re-authorization"


def run_healthcheck(db_path: Optional[str] = None, notify: bool = True) -> dict:
    """Run all health checks and optionally notify via Telegram.

    Returns a dict of check results.
    """
    results = {}

    # Database
    ok, msg = check_database(db_path)
    results["database"] = {"ok": ok, "message": msg}

    # Oura
    ok, msg = check_oura_token()
    results["oura"] = {"ok": ok, "message": msg}

    # Whoop
    ok, msg = check_whoop_token(db_path)
    results["whoop"] = {"ok": ok, "message": msg}

    # Format report
    all_ok = all(r["ok"] for r in results.values())
    status = "✅" if all_ok else "⚠️"

    lines = [f"{status} Healthcheck Report", ""]
    for name, r in results.items():
        icon = "✅" if r["ok"] else "❌"
        lines.append(f"{icon} {name.title()}: {r['message']}")

    report = "\n".join(lines)
    logger.info("Healthcheck: %s", "ALL OK" if all_ok else "ISSUES FOUND")

    if notify:
        send_message(report)

    return results
