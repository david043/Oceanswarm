import pytest

from agents.actions import (
    apply_action,
    check_death,
    consume_from_inventory,
    resolve_interact,
    resolve_move,
    CONSUMPTION_THRESHOLD,
    ENERGY_RESTORE,
)


BASE_AGENT = {
    "id": "a1",
    "x": 50,
    "y": 50,
    "energy": 100.0,
    "is_alive": True,
    "inventory": {},
    "internal_state": {},
}

OTHER_AGENT = {
    "id": "a2",
    "x": 51,
    "y": 50,
    "energy": 80.0,
    "is_alive": True,
    "inventory": {"food": 2},
    "internal_state": {},
}


# ---------------------------------------------------------------------------
# resolve_move
# ---------------------------------------------------------------------------

def test_move_north():
    result = resolve_move(BASE_AGENT, {"direction": "north"})
    assert result["y"] == 49
    assert result["x"] == 50


def test_move_south():
    result = resolve_move(BASE_AGENT, {"direction": "south"})
    assert result["y"] == 51


def test_move_east():
    result = resolve_move(BASE_AGENT, {"direction": "east"})
    assert result["x"] == 51


def test_move_west():
    result = resolve_move(BASE_AGENT, {"direction": "west"})
    assert result["x"] == 49


def test_move_clamps_to_world_boundary():
    agent = {**BASE_AGENT, "x": 0, "y": 0}
    result = resolve_move(agent, {"direction": "north"})
    assert result["y"] == 0
    result = resolve_move(agent, {"direction": "west"})
    assert result["x"] == 0


# ---------------------------------------------------------------------------
# apply_action (general)
# ---------------------------------------------------------------------------

def test_apply_action_deducts_energy():
    result, _ = apply_action(BASE_AGENT, "move", {"direction": "north"})
    assert result["energy"] < BASE_AGENT["energy"]


def test_apply_action_energy_floor():
    agent = {**BASE_AGENT, "energy": 1.0}
    result, _ = apply_action(agent, "communicate", {})
    assert result["energy"] >= 0.0


def test_apply_action_unknown_action_falls_back_to_idle():
    result, _ = apply_action(BASE_AGENT, "fly_to_moon", {})
    assert result["energy"] == BASE_AGENT["energy"] - 0.5  # idle cost


def test_gather_increases_inventory():
    result, _ = apply_action(BASE_AGENT, "gather", {"resource": "food"})
    assert result["inventory"].get("food", 0) > 0


# ---------------------------------------------------------------------------
# consume_from_inventory
# ---------------------------------------------------------------------------

def test_consume_food_when_energy_low():
    agent = {**BASE_AGENT, "energy": 20.0, "inventory": {"food": 1}}
    result = consume_from_inventory(agent)
    assert result["energy"] == 20.0 + ENERGY_RESTORE["food"]
    assert result["inventory"].get("food", 0) == 0


def test_consume_water_when_no_food():
    agent = {**BASE_AGENT, "energy": 20.0, "inventory": {"water": 1}}
    result = consume_from_inventory(agent)
    assert result["energy"] == 20.0 + ENERGY_RESTORE["water"]
    assert result["inventory"].get("water", 0) == 0


def test_food_preferred_over_water():
    agent = {**BASE_AGENT, "energy": 20.0, "inventory": {"food": 1, "water": 1}}
    result = consume_from_inventory(agent)
    assert result["inventory"].get("food", 0) == 0
    assert result["inventory"].get("water", 0) == 1


def test_no_consumption_above_threshold():
    agent = {**BASE_AGENT, "energy": CONSUMPTION_THRESHOLD, "inventory": {"food": 5}}
    result = consume_from_inventory(agent)
    assert result["inventory"]["food"] == 5
    assert result["energy"] == CONSUMPTION_THRESHOLD


def test_tools_never_consumed():
    agent = {**BASE_AGENT, "energy": 10.0, "inventory": {"tools": 3}}
    result = consume_from_inventory(agent)
    assert result["inventory"]["tools"] == 3
    assert result["energy"] == 10.0


def test_consumption_caps_at_100():
    # Patch ENERGY_RESTORE temporarily to force an overshoot
    import agents.actions as actions_module
    original = actions_module.ENERGY_RESTORE.copy()
    actions_module.ENERGY_RESTORE["food"] = 200.0
    try:
        agent = {**BASE_AGENT, "energy": 20.0, "inventory": {"food": 1}}
        result = consume_from_inventory(agent)
        assert result["energy"] == 100.0
    finally:
        actions_module.ENERGY_RESTORE.update(original)


def test_consumption_removes_depleted_key():
    agent = {**BASE_AGENT, "energy": 10.0, "inventory": {"food": 1}}
    result = consume_from_inventory(agent)
    assert "food" not in result["inventory"]


# ---------------------------------------------------------------------------
# check_death
# ---------------------------------------------------------------------------

def test_check_death_marks_dead_at_zero():
    agent = {**BASE_AGENT, "energy": 0.0}
    result = check_death(agent)
    assert result["is_alive"] is False


def test_check_death_survives_above_zero():
    agent = {**BASE_AGENT, "energy": 0.1}
    result = check_death(agent)
    assert result["is_alive"] is True


def test_apply_action_kills_agent_when_energy_depleted():
    agent = {**BASE_AGENT, "energy": 0.4}  # idle costs 0.5
    result, _ = apply_action(agent, "idle", {})
    assert result["is_alive"] is False


# ---------------------------------------------------------------------------
# resolve_interact
# ---------------------------------------------------------------------------

def test_fight_actor_loses_energy():
    actor, _ = resolve_interact(
        BASE_AGENT, {"target_id": "a2", "type": "fight"}, [OTHER_AGENT]
    )
    assert actor["energy"] == BASE_AGENT["energy"] - 3.0


def test_fight_target_loses_energy():
    _, target = resolve_interact(
        BASE_AGENT, {"target_id": "a2", "type": "fight"}, [OTHER_AGENT]
    )
    assert target["energy"] == OTHER_AGENT["energy"] - 5.0


def test_fight_floors_energy_at_zero():
    weak_actor = {**BASE_AGENT, "energy": 1.0}
    weak_target = {**OTHER_AGENT, "energy": 2.0}
    actor, target = resolve_interact(
        weak_actor, {"target_id": "a2", "type": "fight"}, [weak_target]
    )
    assert actor["energy"] == 0.0
    assert target["energy"] == 0.0


def test_trade_transfers_item_to_target():
    actor = {**BASE_AGENT, "inventory": {"food": 3}}
    actor_result, target_result = resolve_interact(
        actor, {"target_id": "a2", "type": "trade"}, [OTHER_AGENT]
    )
    assert actor_result["inventory"]["food"] == 2
    assert target_result["inventory"]["food"] == OTHER_AGENT["inventory"]["food"] + 1


def test_trade_no_op_when_empty_inventory():
    actor_result, target_result = resolve_interact(
        BASE_AGENT, {"target_id": "a2", "type": "trade"}, [OTHER_AGENT]
    )
    assert target_result is None
    assert actor_result["inventory"] == {}


def test_trade_removes_depleted_item_key():
    actor = {**BASE_AGENT, "inventory": {"food": 1}}
    actor_result, _ = resolve_interact(
        actor, {"target_id": "a2", "type": "trade"}, [OTHER_AGENT]
    )
    assert "food" not in actor_result["inventory"]


def test_help_transfers_energy():
    actor_result, target_result = resolve_interact(
        BASE_AGENT, {"target_id": "a2", "type": "help"}, [OTHER_AGENT]
    )
    assert actor_result["energy"] == BASE_AGENT["energy"] - 10.0
    assert target_result["energy"] == OTHER_AGENT["energy"] + 10.0


def test_help_caps_target_at_100():
    full_target = {**OTHER_AGENT, "energy": 95.0}
    _, target_result = resolve_interact(
        BASE_AGENT, {"target_id": "a2", "type": "help"}, [full_target]
    )
    assert target_result["energy"] == 100.0


def test_help_floors_actor_at_zero():
    weak_actor = {**BASE_AGENT, "energy": 5.0}
    actor_result, target_result = resolve_interact(
        weak_actor, {"target_id": "a2", "type": "help"}, [OTHER_AGENT]
    )
    assert actor_result["energy"] == 0.0
    assert target_result["energy"] == OTHER_AGENT["energy"] + 5.0


def test_interact_returns_none_when_no_target_id():
    _, target = resolve_interact(BASE_AGENT, {"type": "fight"}, [OTHER_AGENT])
    assert target is None


def test_interact_returns_none_when_target_not_found():
    _, target = resolve_interact(
        BASE_AGENT, {"target_id": "unknown", "type": "fight"}, [OTHER_AGENT]
    )
    assert target is None
