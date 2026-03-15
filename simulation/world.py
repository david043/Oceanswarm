"""World state: grid, proximity detection, and resource layout."""
import math

from config import settings


def euclidean_distance(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def find_nearby_agents(
    agent_id: str,
    ax: int,
    ay: int,
    all_agents: list[dict],
    radius: int | None = None,
) -> list[dict]:
    """Return agents within interaction radius, excluding the agent itself."""
    radius = radius or settings.interaction_radius
    nearby = []
    for other in all_agents:
        if other["id"] == agent_id or not other.get("is_alive", True):
            continue
        dist = euclidean_distance(ax, ay, other["x"], other["y"])
        if dist <= radius:
            nearby.append({**other, "distance": dist})
    return sorted(nearby, key=lambda a: a["distance"])


def random_spawn_position(occupied: list[tuple[int, int]]) -> tuple[int, int]:
    """Find a random unoccupied position on the grid."""
    import random

    occupied_set = set(occupied)
    for _ in range(1000):
        x = random.randint(0, settings.world_width - 1)
        y = random.randint(0, settings.world_height - 1)
        if (x, y) not in occupied_set:
            return x, y
    # Fallback: just return a random position even if occupied
    return random.randint(0, settings.world_width - 1), random.randint(0, settings.world_height - 1)
