"""Ecovacs Deebot control layer (via deebot-client, the library Home Assistant uses).

Each call opens a fresh connection, does one thing, and closes it. Slower than a
persistent link (a few seconds), but nothing to keep alive or reconnect.

CLI, for Claude Code or a terminal:
    python vacuum.py status
    python vacuum.py rooms
    python vacuum.py clean [--rooms "kitchen,bathroom"] [--mode vacuum|both|mop_after|mop]
                           [--suction quiet|standard|strong|max] [--water low|medium|high|highest]
    python vacuum.py pause | resume | dock
"""

import argparse
import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load home-bot's .env explicitly so this module works from home-bot, Jarvis, or the CLI.
load_dotenv(Path(__file__).resolve().parent / ".env")

ECOVACS_EMAIL = os.environ.get("ECOVACS_EMAIL", "")
ECOVACS_PASSWORD = os.environ.get("ECOVACS_PASSWORD", "")
ECOVACS_COUNTRY = os.environ.get("ECOVACS_COUNTRY", "US")

# Plain words -> library enum names. The app offers vacuum, both, and mop after vacuum.
MODE_WORDS = {
    "vacuum": "VACUUM", "vac": "VACUUM", "vacuum_only": "VACUUM", "sweep": "VACUUM",
    "both": "VACUUM_AND_MOP", "vacuum_and_mop": "VACUUM_AND_MOP", "mop": "VACUUM_AND_MOP",
    "mop_after": "MOP_AFTER_VACUUM", "mop_after_vacuum": "MOP_AFTER_VACUUM",
    "mop_only": "MOP",
}
SUCTION_WORDS = {"quiet": "QUIET", "standard": "NORMAL", "normal": "NORMAL",
                 "strong": "MAX", "max": "MAX_PLUS", "max_plus": "MAX_PLUS"}
# Water levels as a share of the slider, for models with a custom 0-N water amount.
WATER_WORDS = {"low": 0.25, "medium": 0.5, "high": 0.75, "highest": 1.0, "ultrahigh": 1.0}
WATER_ENUM = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH", "highest": "ULTRAHIGH", "ultrahigh": "ULTRAHIGH"}


def _norm(word: str) -> str:
    return word.strip().lower().replace(" ", "_").replace("-", "_")


def parse_mode(word: str) -> str:
    """Map a plain word ('mop', 'both', 'vacuum') to a WorkMode name."""
    key = _norm(word)
    if key not in MODE_WORDS:
        raise ValueError(f"Unknown mode '{word}'. Use vacuum, both, mop_after, or mop_only.")
    return MODE_WORDS[key]


def match_rooms(wanted: list[str], rooms: dict[str, int]) -> list[int]:
    """Match room names case-insensitively to room ids. rooms is {name: id}."""
    by_name = {_norm(n): i for n, i in rooms.items()}
    ids, missing = [], []
    for w in wanted:
        if _norm(w) in by_name:
            ids.append(by_name[_norm(w)])
        else:
            missing.append(w)
    if missing:
        raise ValueError(f"Unknown room(s): {', '.join(missing)}. Rooms: {', '.join(rooms)}")
    return ids


# ---- Connection ----

@asynccontextmanager
async def _connect():
    import aiohttp
    from deebot_client.api_client import ApiClient
    from deebot_client.authentication import Authenticator, create_rest_config
    from deebot_client.device import Device
    from deebot_client.mqtt_client import MqttClient, create_mqtt_config
    from deebot_client.util import md5

    if not ECOVACS_EMAIL or not ECOVACS_PASSWORD:
        raise RuntimeError("ECOVACS_EMAIL and ECOVACS_PASSWORD are not set in home-bot/.env")

    device_id = md5(str(time.time()))
    async with aiohttp.ClientSession() as session:
        rest = create_rest_config(session, device_id=device_id, alpha_2_country=ECOVACS_COUNTRY)
        auth = Authenticator(rest, ECOVACS_EMAIL, md5(ECOVACS_PASSWORD))
        devices = await ApiClient(auth).get_devices()
        if not devices.mqtt:
            raise RuntimeError("No supported Deebot found on this Ecovacs account")
        bot = Device(devices.mqtt[0], auth)
        mqtt = MqttClient(create_mqtt_config(device_id=device_id, country=ECOVACS_COUNTRY), auth)
        await bot.initialize(mqtt)
        try:
            yield bot
        finally:
            await bot.teardown()
            await mqtt.disconnect()
            await auth.teardown()


async def _fetch(bot, event_cls, timeout: float = 8):
    """Subscribe to an event (which triggers a refresh) and wait for the first value."""
    fut = asyncio.get_running_loop().create_future()

    async def on_event(event):
        if not fut.done():
            fut.set_result(event)

    unsub = bot.events.subscribe(event_cls, on_event)
    try:
        return await asyncio.wait_for(fut, timeout)
    except TimeoutError:
        return None
    finally:
        unsub()


async def _rooms(bot) -> dict[str, int]:
    from deebot_client.events import RoomsEvent
    if not bot.capabilities.map:
        return {}
    ev = await _fetch(bot, RoomsEvent, timeout=15)
    return {r.name: r.id for r in ev.rooms} if ev else {}


# ---- Actions ----

async def get_status() -> dict:
    from deebot_client.events import BatteryEvent, FanSpeedEvent, StateEvent, WorkModeEvent
    async with _connect() as bot:
        caps = bot.capabilities
        out = {"name": bot.device_info.get("nick") or "Deebot"}
        if ev := await _fetch(bot, StateEvent):
            out["state"] = ev.state.name.lower()
        if ev := await _fetch(bot, BatteryEvent):
            out["battery"] = ev.value
        if caps.clean.work_mode and (ev := await _fetch(bot, WorkModeEvent)):
            out["mode"] = ev.mode.name.lower()
        if caps.fan_speed and (ev := await _fetch(bot, FanSpeedEvent)):
            out["suction"] = ev.speed.name.lower()
        return out


async def list_rooms() -> list[str]:
    async with _connect() as bot:
        return list((await _rooms(bot)).keys())


async def _apply_settings(bot, mode, suction, water) -> list[str]:
    from deebot_client.capabilities import CapabilityNumber
    from deebot_client.events import FanSpeedLevel, WaterAmount, WorkMode

    caps, done = bot.capabilities, []
    if mode:
        name = parse_mode(mode)
        wm = caps.clean.work_mode
        if not wm or WorkMode[name] not in wm.types:
            have = ", ".join(t.name.lower() for t in wm.types) if wm else "none"
            raise ValueError(f"This robot can't do {name.lower()}. Modes: {have}")
        await bot.execute_command(wm.set(WorkMode[name]))
        done.append(name.lower().replace("_", " "))
    if suction:
        key = _norm(suction)
        if key not in SUCTION_WORDS or not caps.fan_speed:
            raise ValueError(f"Unknown suction '{suction}'. Use quiet, standard, strong, or max.")
        await bot.execute_command(caps.fan_speed.set(FanSpeedLevel[SUCTION_WORDS[key]]))
        done.append(f"{key} suction")
    if water:
        key = _norm(water)
        if key not in WATER_WORDS or not caps.water:
            raise ValueError(f"Unknown water level '{water}'. Use low, medium, high, or highest.")
        amount = caps.water.amount
        if isinstance(amount, CapabilityNumber):
            value = round(amount.min + (amount.max - amount.min) * WATER_WORDS[key])
            await bot.execute_command(amount.set(value))
        else:
            await bot.execute_command(amount.set(WaterAmount[WATER_ENUM[key]]))
        done.append(f"{key} water")
    return done


async def start_clean(rooms: list[str] | None = None, mode: str | None = None,
                      suction: str | None = None, water: str | None = None) -> str:
    """Start cleaning the whole home or the named rooms. Unset options keep the app's settings."""
    from deebot_client.models import CleanAction, CleanMode
    async with _connect() as bot:
        action = bot.capabilities.clean.action
        ids = match_rooms(rooms, await _rooms(bot)) if rooms else []
        settings = await _apply_settings(bot, mode, suction, water)
        if ids:
            await bot.execute_command(action.area(CleanMode.SPOT_AREA, ids, 1))
            where = ", ".join(rooms)
        else:
            await bot.execute_command(action.command(CleanAction.START))
            where = "the whole home"
        extra = f" ({', '.join(settings)})" if settings else ""
        return f"Cleaning {where}{extra}."


async def pause() -> str:
    from deebot_client.models import CleanAction
    async with _connect() as bot:
        await bot.execute_command(bot.capabilities.clean.action.command(CleanAction.PAUSE))
        return "Paused."


async def resume() -> str:
    from deebot_client.models import CleanAction
    async with _connect() as bot:
        await bot.execute_command(bot.capabilities.clean.action.command(CleanAction.RESUME))
        return "Resumed."


async def dock() -> str:
    async with _connect() as bot:
        await bot.execute_command(bot.capabilities.charge.execute())
        return "Heading back to the station."


def main() -> None:
    p = argparse.ArgumentParser(description="Control the Ecovacs Deebot")
    p.add_argument("action", choices=["status", "rooms", "clean", "pause", "resume", "dock"])
    p.add_argument("--rooms", help="Comma-separated room names; omit for the whole home")
    p.add_argument("--mode", help="vacuum, both, mop_after, or mop_only")
    p.add_argument("--suction", help="quiet, standard, strong, or max")
    p.add_argument("--water", help="low, medium, high, or highest")
    a = p.parse_args()
    logging.basicConfig(level=logging.WARNING)

    if a.action == "status":
        result = asyncio.run(get_status())
    elif a.action == "rooms":
        result = asyncio.run(list_rooms())
    elif a.action == "clean":
        rooms = [r for r in (a.rooms or "").split(",") if r.strip()] or None
        result = asyncio.run(start_clean(rooms, a.mode, a.suction, a.water))
    else:
        result = asyncio.run({"pause": pause, "resume": resume, "dock": dock}[a.action]())
    print(json.dumps(result, indent=2) if not isinstance(result, str) else result)


if __name__ == "__main__":
    main()
