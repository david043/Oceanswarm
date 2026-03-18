"""Human-readable formatting for tick summaries."""
from datetime import datetime


def format_tick_summary(summary: dict) -> str:
    tick = summary["tick"]
    now = datetime.now().strftime("%H:%M:%S")
    narrative = summary.get("narrative", "").strip()
    return f"Tick {tick} @ {now}\n  {narrative}" if narrative else f"Tick {tick} @ {now}"
