"""Weather-based auto-detection for climate preset."""

import logging
from typing import Optional

import requests

from config import ZIP_CODE

logger = logging.getLogger(__name__)

# Open-Meteo API — free, no API key needed
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Temperature thresholds (Fahrenheit)
COLD_THRESHOLD = 45  # Below this → winter mode
HOT_THRESHOLD = 75   # Above this → summer mode


def get_current_temp(zip_code: Optional[str] = None) -> Optional[float]:
    """Get current temperature in Fahrenheit for the given zip code."""
    zc = zip_code or ZIP_CODE
    try:
        # Geocode zip to lat/lon
        geo_resp = requests.get(
            GEOCODE_URL,
            params={"name": zc, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        geo_resp.raise_for_status()
        results = geo_resp.json().get("results", [])
        if not results:
            logger.warning("Could not geocode zip %s", zc)
            return None

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]

        # Get current weather
        weather_resp = requests.get(
            WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m",
                "temperature_unit": "fahrenheit",
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        current = weather_resp.json().get("current", {})
        temp = current.get("temperature_2m")
        logger.info("Current temp for %s: %.1f°F", zc, temp)
        return temp

    except Exception as e:
        logger.error("Weather fetch failed: %s", e)
        return None


def auto_detect_command() -> str:
    """Pick the right start command based on current temperature.

    Returns: 'start-winter', 'start-summer', or 'start' (mild).
    """
    temp = get_current_temp()
    if temp is None:
        return "start"  # Fallback to default if weather unavailable

    if temp < COLD_THRESHOLD:
        return "start-winter"
    elif temp > HOT_THRESHOLD:
        return "start-summer"
    else:
        return "start"
