"""External world events that agents can perceive."""
from dataclasses import dataclass, field


@dataclass
class WorldEvent:
    event_type: str
    description: str
    data: dict = field(default_factory=dict)


PREDEFINED_EVENTS: dict[str, WorldEvent] = {
    "market_crash": WorldEvent(
        event_type="market_crash",
        description="Markets have crashed — resources are scarce and trade is difficult.",
    ),
    "market_boom": WorldEvent(
        event_type="market_boom",
        description="Markets are booming — resources are abundant and trade is profitable.",
    ),
    "storm": WorldEvent(
        event_type="storm",
        description="A violent storm is sweeping across the world — movement is dangerous.",
    ),
    "drought": WorldEvent(
        event_type="drought",
        description="A severe drought has struck — water and food are very hard to find.",
    ),
    "war": WorldEvent(
        event_type="war",
        description="A war has broken out — conflict and danger are everywhere.",
    ),
    "peace": WorldEvent(
        event_type="peace",
        description="A period of peace has begun — cooperation and trade are flourishing.",
    ),
    "plague": WorldEvent(
        event_type="plague",
        description="A plague is spreading — agents with low energy are at risk.",
    ),
}
