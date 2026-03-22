"""Action resolution: applies an agent's chosen action to the world state."""
import random

from config import settings


ENERGY_COSTS: dict[str, float] = {
    "move": 2.0,
    "communicate": 0.5,
    "interact": 0.0,   # all interact costs are handled inside resolve_interact
    "gather": 4.0,
    "idle": 0.5,
}

VALID_ACTIONS = set(ENERGY_COSTS.keys())
VALID_DIRECTIONS = {"north", "south", "east", "west"}

ENERGY_RESTORE: dict[str, float] = {
    "food": 20.0,
    "water": 10.0,
}
CONSUMPTION_THRESHOLD: float = 30.0


def consume_from_inventory(agent_data: dict) -> dict:
    """If energy is below threshold, consume one unit of food or water (food first)."""
    if agent_data["energy"] >= CONSUMPTION_THRESHOLD:
        return agent_data
    inventory = dict(agent_data.get("inventory", {}))
    for resource in ("food", "water"):
        if inventory.get(resource, 0) > 0:
            inventory[resource] -= 1
            if inventory[resource] == 0:
                del inventory[resource]
            energy = min(100.0, agent_data["energy"] + ENERGY_RESTORE[resource])
            return {**agent_data, "energy": energy, "inventory": inventory}
    return agent_data


def check_death(agent_data: dict) -> dict:
    """Mark agent as permanently dead if energy has reached zero."""
    if agent_data["energy"] <= 0.0:
        return {**agent_data, "is_alive": False, "status": "dead"}
    return agent_data


def resolve_move(agent_data: dict, parameters: dict) -> dict:
    direction = parameters.get("direction", "").lower()
    if direction not in VALID_DIRECTIONS:
        return agent_data

    steps = max(1, min(10, int(parameters.get("steps", 1))))

    x, y = agent_data["x"], agent_data["y"]
    if direction == "north":
        y = max(0, y - steps)
    elif direction == "south":
        y = min(settings.world_height - 1, y + steps)
    elif direction == "west":
        x = max(0, x - steps)
    elif direction == "east":
        x = min(settings.world_width - 1, x + steps)

    return {**agent_data, "x": x, "y": y}


def resolve_gather(agent_data: dict, parameters: dict) -> dict:
    resource = parameters.get("resource", "food")
    inventory = dict(agent_data.get("inventory", {}))
    inventory[resource] = inventory.get(resource, 0) + random.randint(1, 3)
    # Gathering restores a little energy
    energy = min(100.0, agent_data["energy"] + 5.0)
    return {**agent_data, "inventory": inventory, "energy": energy}


def resolve_communicate(agent_data: dict, parameters: dict) -> dict:
    """Communicate has no direct state effect beyond energy cost; content is propagated by the engine."""
    return agent_data


def resolve_interact(
    agent_data: dict,
    parameters: dict,
    all_agents: list[dict],
) -> tuple[dict, dict | None]:
    """
    Apply interaction effects between actor and target.
    Returns (updated_actor, updated_target) or (updated_actor, None) if no valid target.
    """
    target_id = parameters.get("target_id")
    interaction_type = parameters.get("type", "")

    target = next((a for a in all_agents if a["id"] == target_id), None)
    if target is None:
        return agent_data, None

    actor = agent_data

    if interaction_type == "fight":
        actor = {**actor, "energy": max(0.0, actor["energy"] - 3.0)}
        target = {**target, "energy": max(0.0, target["energy"] - 5.0)}

    elif interaction_type == "trade":
        inventory = {k: v for k, v in actor.get("inventory", {}).items() if v > 0}
        if not inventory:
            return actor, None
        item = random.choice(list(inventory.keys()))
        actor_inv = dict(actor.get("inventory", {}))
        actor_inv[item] -= 1
        if actor_inv[item] == 0:
            del actor_inv[item]
        target_inv = dict(target.get("inventory", {}))
        target_inv[item] = target_inv.get(item, 0) + 1
        actor = {**actor, "inventory": actor_inv}
        target = {**target, "inventory": target_inv}

    elif interaction_type == "help":
        transfer = min(10.0, actor["energy"])
        actor = {**actor, "energy": max(0.0, actor["energy"] - transfer)}
        target = {**target, "energy": min(100.0, target["energy"] + transfer)}

    return actor, target


def apply_action(
    agent_data: dict,
    action: str,
    parameters: dict,
    all_agents: list[dict] | None = None,
) -> tuple[dict, dict | None]:
    """
    Apply action side effects and deduct energy.
    Returns (updated_actor, updated_target_or_None).
    """
    agent_data = consume_from_inventory(agent_data)

    action = action if action in VALID_ACTIONS else "idle"
    cost = ENERGY_COSTS[action]
    updated = {**agent_data, "energy": max(0.0, agent_data["energy"] - cost)}

    target_update: dict | None = None

    if action == "move":
        updated = resolve_move(updated, parameters)
    elif action == "gather":
        updated = resolve_gather(updated, parameters)
    elif action == "communicate":
        updated = resolve_communicate(updated, parameters)
    elif action == "interact":
        updated, target_update = resolve_interact(updated, parameters, all_agents or [])

    updated = check_death(updated)
    if target_update is not None:
        target_update = check_death(target_update)

    return updated, target_update
