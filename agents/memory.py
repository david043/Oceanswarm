"""Rolling memory window for agents."""
from config import settings


def add_memory(memory: list[str], new_entry: str | None) -> list[str]:
    """Append a new memory and trim to the configured window size."""
    if not new_entry:
        return memory
    updated = memory + [new_entry]
    return updated[-settings.max_agent_memory:]
