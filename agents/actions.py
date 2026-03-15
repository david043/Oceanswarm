"""Action resolution: applies an agent's chosen action to the world state."""
import random

from config import settings


ENERGY_COSTS: dict[str, float] = {
    "move": 2.0,
    "communicate": 0.5,
    "interact": 3.0,
    "gather": 4.0,
    "idle": 0.5,
}

VALID_ACTIONS = set(ENERGY_COSTS.keys())
VALID_DIRECTIONS = {"north", "south", "east", "west"}


def resolve_move(agent_data: dict, parameters: dict) -> dict:
    direction = parameters.get("direction", "").lower()
    if direction not in VALID_DIRECTIONS:
        return agent_data

    x, y = agent_data["x"], agent_data["y"]
    if direction == "north":
        y = max(0, y - 1)
    elif direction == "south":
        y = min(settings.world_height - 1, y + 1)
    elif direction == "west":
        x = max(0, x - 1)
    elif direction == "east":
        x = min(settings.world_width - 1, x + 1)

    return {**agent_data, "x": x, "y": y}


def resolve_gather(agent_data: dict, parameters: dict) -> dict:
    resource = parameters.get("resource", "food")
    inventory = dict(agent_data.get("inventory", {}))
    inventory[resource] = inventory.get(resource, 0) + random.randint(1, 3)
    # Gathering restores a little energy
    energy = min(100.0, agent_data["energy"] + 5.0)
    return {**agent_data, "inventory": inventory, "energy": energy}


def apply_action(agent_data: dict, action: str, parameters: dict) -> dict:
    """Apply action side effects and deduct energy. Returns updated agent_data."""
    action = action if action in VALID_ACTIONS else "idle"
    cost = ENERGY_COSTS[action]
    updated = {**agent_data, "energy": max(0.0, agent_data["energy"] - cost)}

    if action == "move":
        updated = resolve_move(updated, parameters)
    elif action == "gather":
        updated = resolve_gather(updated, parameters)
    # communicate / interact / idle: no extra state change here;
    # social effects (relationships, resource transfers) will come in a later iteration.

    return updated
