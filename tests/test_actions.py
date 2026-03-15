import pytest

from agents.actions import apply_action, resolve_move


BASE_AGENT = {
    "id": "a1",
    "x": 50,
    "y": 50,
    "energy": 100.0,
    "inventory": {},
    "internal_state": {},
}


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


def test_apply_action_deducts_energy():
    result = apply_action(BASE_AGENT, "move", {"direction": "north"})
    assert result["energy"] < BASE_AGENT["energy"]


def test_apply_action_energy_floor():
    agent = {**BASE_AGENT, "energy": 1.0}
    result = apply_action(agent, "interact", {})
    assert result["energy"] >= 0.0


def test_apply_action_unknown_action_falls_back_to_idle():
    result = apply_action(BASE_AGENT, "fly_to_moon", {})
    assert result["energy"] == BASE_AGENT["energy"] - 0.5  # idle cost


def test_gather_increases_inventory():
    result = apply_action(BASE_AGENT, "gather", {"resource": "food"})
    assert result["inventory"].get("food", 0) > 0
