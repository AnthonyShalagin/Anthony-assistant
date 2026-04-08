"""Trend calculation for health metrics.

Computes 7-day and 30-day averages and trend arrows (↑↓→).
"""

import logging
from dataclasses import dataclass
from typing import Optional

from database import get_db, get_metric_average

logger = logging.getLogger(__name__)

# Threshold for trend change (percentage)
TREND_THRESHOLD = 5.0


@dataclass
class MetricTrend:
    """A single metric's trend data."""
    metric_name: str
    source: str
    avg_7d: Optional[float]
    avg_30d: Optional[float]
    arrow: str  # ↑ ↓ →
    display_value: str  # formatted for Telegram

    @property
    def available(self) -> bool:
        return self.avg_7d is not None


def compute_arrow(avg_7d: Optional[float], avg_30d: Optional[float]) -> str:
    """Compute trend arrow based on 7-day vs 30-day average.

    ↑ = 7-day avg is ≥ TREND_THRESHOLD% above 30-day avg
    ↓ = 7-day avg is ≥ TREND_THRESHOLD% below 30-day avg
    → = stable (within threshold)
    """
    if avg_7d is None or avg_30d is None or avg_30d == 0:
        return "—"
    pct_change = ((avg_7d - avg_30d) / abs(avg_30d)) * 100
    if pct_change >= TREND_THRESHOLD:
        return "↑"
    elif pct_change <= -TREND_THRESHOLD:
        return "↓"
    return "→"


def format_value(value: Optional[float], unit: str = "", decimals: int = 0) -> str:
    """Format a metric value for display."""
    if value is None:
        return "—"
    if decimals == 0:
        return f"{int(round(value))}{unit}"
    return f"{value:.{decimals}f}{unit}"


# Metrics to track: (metric_name, source, unit, decimals, display_name)
TRACKED_METRICS = [
    # Oura
    ("sleep_score", "oura", "", 0, "Sleep Score"),
    ("readiness_score", "oura", "", 0, "Readiness"),
    ("activity_score", "oura", "", 0, "Activity"),
    ("hrv_average", "oura", "ms", 0, "HRV (Oura)"),
    # Whoop
    ("recovery_score", "whoop", "%", 0, "Recovery"),
    ("strain_score", "whoop", "", 1, "Strain"),
    ("hrv_rmssd", "whoop", "ms", 0, "HRV (Whoop)"),
    ("sleep_performance", "whoop", "%", 0, "Sleep Perf"),
    # Garmin
    ("steps", "garmin", "", 0, "Steps"),
    ("body_battery_high", "garmin", "", 0, "Body Battery"),
    ("avg_stress", "garmin", "", 0, "Stress"),
]


def get_all_trends(db_path: Optional[str] = None) -> list[MetricTrend]:
    """Calculate trends for all tracked metrics."""
    trends = []
    db_kwargs = {"db_path": db_path} if db_path else {}

    with get_db(**db_kwargs) as conn:
        for metric_name, source, unit, decimals, display_name in TRACKED_METRICS:
            avg_7d = get_metric_average(conn, source, metric_name, days=7)
            avg_30d = get_metric_average(conn, source, metric_name, days=30)
            arrow = compute_arrow(avg_7d, avg_30d)
            display = format_value(avg_7d, unit, decimals)

            trends.append(MetricTrend(
                metric_name=metric_name,
                source=source,
                avg_7d=avg_7d,
                avg_30d=avg_30d,
                arrow=arrow,
                display_value=f"{display_name}: {display} {arrow}",
            ))

    return trends


def format_trends_block(trends: list[MetricTrend]) -> str:
    """Format trends into a readable text block for the briefing."""
    lines = []
    available = [t for t in trends if t.available]
    missing_sources = set()

    for t in trends:
        if not t.available:
            missing_sources.add(t.source)

    if available:
        # Group by source
        by_source = {}
        for t in available:
            by_source.setdefault(t.source.title(), []).append(t.display_value)

        for source, metrics in by_source.items():
            lines.append(f"📊 {source}:")
            for m in metrics:
                lines.append(f"  {m}")
            lines.append("")

    if missing_sources:
        lines.append(f"⚠️ No data from: {', '.join(sorted(missing_sources))}")

    return "\n".join(lines).strip()
