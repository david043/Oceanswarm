from unittest.mock import patch

from agents.memory import add_memory


def test_add_memory_appends():
    result = add_memory(["old memory"], "new memory")
    assert result == ["old memory", "new memory"]


def test_add_memory_trims_to_max():
    with patch("agents.memory.settings") as mock_settings:
        mock_settings.max_agent_memory = 3
        memory = ["a", "b", "c"]
        result = add_memory(memory, "d")
        assert result == ["b", "c", "d"]
        assert len(result) == 3


def test_add_memory_ignores_none():
    memory = ["a", "b"]
    result = add_memory(memory, None)
    assert result == ["a", "b"]


def test_add_memory_empty_start():
    result = add_memory([], "first memory")
    assert result == ["first memory"]
