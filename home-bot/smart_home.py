"""SmartRent device control layer."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from smartrent import async_login

logger = logging.getLogger(__name__)

# Load home-bot's .env explicitly so this module works whether
# imported from home-bot or reused from Jarvis.
_HOME_BOT_DIR = Path(__file__).resolve().parent
load_dotenv(_HOME_BOT_DIR / ".env")

SMARTRENT_EMAIL = os.environ.get("SMARTRENT_EMAIL", "")
SMARTRENT_PASSWORD = os.environ.get("SMARTRENT_PASSWORD", "")

_api = None


async def _get_api():
    """Get or create SmartRent API connection."""
    global _api
    if _api is None:
        logger.info("Connecting to SmartRent...")
        _api = await async_login(SMARTRENT_EMAIL, SMARTRENT_PASSWORD)
        logger.info("SmartRent connected")
    return _api


async def get_thermostat_status() -> dict:
    """Get current thermostat state."""
    api = await _get_api()
    thermos = api.get_thermostats()
    if not thermos:
        return {"error": "No thermostat found"}

    t = thermos[0]
    return {
        "current_temp": t.get_current_temp(),
        "current_humidity": t.get_current_humidity(),
        "cooling_setpoint": t.get_cooling_setpoint(),
        "heating_setpoint": t.get_heating_setpoint(),
        "mode": t.get_mode(),
        "fan_mode": t.get_fan_mode(),
        "name": t.get_name(),
    }


async def set_thermostat(temperature: int, mode: str = "cool") -> str:
    """Set thermostat temperature and mode."""
    api = await _get_api()
    thermos = api.get_thermostats()
    if not thermos:
        return "No thermostat found"

    t = thermos[0]

    # Set mode
    mode = mode.lower()
    if mode in ("cool", "cooling"):
        await t.async_set_mode("cool")
        await t.async_set_cooling_setpoint(temperature)
    elif mode in ("heat", "heating"):
        await t.async_set_mode("heat")
        await t.async_set_heating_setpoint(temperature)
    elif mode in ("auto",):
        await t.async_set_mode("auto")
        await t.async_set_cooling_setpoint(temperature + 2)
        await t.async_set_heating_setpoint(temperature - 2)
    elif mode in ("off",):
        await t.async_set_mode("off")
        return "Thermostat turned off."
    else:
        await t.async_set_mode("cool")
        await t.async_set_cooling_setpoint(temperature)

    return f"Thermostat set to {temperature}°F in {mode} mode."


async def get_lock_status() -> dict:
    """Get current lock state."""
    api = await _get_api()
    locks = api.get_locks()
    if not locks:
        return {"error": "No lock found"}

    lock = locks[0]
    return {
        "locked": lock.get_locked(),
        "name": lock.get_name(),
    }


async def set_lock(locked: bool) -> str:
    """Lock or unlock the door."""
    api = await _get_api()
    locks = api.get_locks()
    if not locks:
        return "No lock found"

    lock = locks[0]
    await lock.async_set_locked(locked)
    action = "locked" if locked else "unlocked"
    name = lock.get_name()
    return f"{name} is now {action}."


async def get_sensor_status() -> list[dict]:
    """Get status of all sensors."""
    api = await _get_api()
    sensors = api.get_leak_sensors()
    results = []
    for s in sensors:
        results.append({
            "name": s.get_name(),
            "leak": s.get_leak(),
        })
    return results


def run_async(coro):
    """Run an async function from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
