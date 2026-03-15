import pytest

from simulation.world import euclidean_distance, find_nearby_agents


def test_euclidean_distance():
    assert euclidean_distance(0, 0, 3, 4) == 5.0
    assert euclidean_distance(0, 0, 0, 0) == 0.0


def test_find_nearby_agents_excludes_self():
    agents = [
        {"id": "a1", "x": 0, "y": 0, "is_alive": True, "name": "Alice"},
        {"id": "a2", "x": 2, "y": 0, "is_alive": True, "name": "Bob"},
    ]
    result = find_nearby_agents("a1", 0, 0, agents, radius=5)
    ids = [a["id"] for a in result]
    assert "a1" not in ids
    assert "a2" in ids


def test_find_nearby_agents_radius_filter():
    agents = [
        {"id": "a1", "x": 0, "y": 0, "is_alive": True, "name": "Alice"},
        {"id": "a2", "x": 3, "y": 0, "is_alive": True, "name": "Bob"},   # distance 3
        {"id": "a3", "x": 10, "y": 0, "is_alive": True, "name": "Carol"},  # distance 10
    ]
    result = find_nearby_agents("a1", 0, 0, agents, radius=5)
    ids = [a["id"] for a in result]
    assert "a2" in ids
    assert "a3" not in ids


def test_find_nearby_agents_excludes_dead():
    agents = [
        {"id": "a1", "x": 0, "y": 0, "is_alive": True, "name": "Alice"},
        {"id": "a2", "x": 1, "y": 0, "is_alive": False, "name": "Dead"},
    ]
    result = find_nearby_agents("a1", 0, 0, agents, radius=5)
    assert result == []


def test_find_nearby_agents_sorted_by_distance():
    agents = [
        {"id": "a1", "x": 0, "y": 0, "is_alive": True, "name": "Alice"},
        {"id": "a3", "x": 4, "y": 0, "is_alive": True, "name": "Carol"},
        {"id": "a2", "x": 1, "y": 0, "is_alive": True, "name": "Bob"},
    ]
    result = find_nearby_agents("a1", 0, 0, agents, radius=10)
    assert result[0]["id"] == "a2"
    assert result[1]["id"] == "a3"
