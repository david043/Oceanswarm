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


MIN_SPAWN_DISTANCE = 3


def random_spawn_position(occupied: list[tuple[int, int]]) -> tuple[int, int]:
    """Find a random position at least MIN_SPAWN_DISTANCE cells from all others."""
    import random

    for _ in range(2000):
        x = random.randint(0, settings.world_width - 1)
        y = random.randint(0, settings.world_height - 1)
        if all(euclidean_distance(x, y, ox, oy) >= MIN_SPAWN_DISTANCE for ox, oy in occupied):
            return x, y
    # Fallback: just avoid exact overlap
    occupied_set = set(occupied)
    for _ in range(1000):
        x = random.randint(0, settings.world_width - 1)
        y = random.randint(0, settings.world_height - 1)
        if (x, y) not in occupied_set:
            return x, y
    return random.randint(0, settings.world_width - 1), random.randint(0, settings.world_height - 1)


def spread_overlapping_agents(agents: list[tuple[str, int, int]]) -> dict[str, tuple[int, int]]:
    """Return {agent_id: (new_x, new_y)} for any agents closer than MIN_SPAWN_DISTANCE to another.
    Agents are processed in order; the second of a too-close pair gets moved."""
    import random

    positions: list[tuple[int, int]] = []
    moves: dict[str, tuple[int, int]] = {}

    for agent_id, x, y in agents:
        if any(euclidean_distance(x, y, ox, oy) < MIN_SPAWN_DISTANCE for ox, oy in positions):
            new_x, new_y = random_spawn_position(positions)
            moves[agent_id] = (new_x, new_y)
            positions.append((new_x, new_y))
        else:
            positions.append((x, y))

    return moves
