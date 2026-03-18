"""Pydantic schemas for agent data flowing in and out of the system."""
from pydantic import BaseModel, Field


class NearbyAgent(BaseModel):
    id: str
    name: str
    distance: float
    last_message: str | None = None


class AgentContext(BaseModel):
    """Full context passed to the LLM each tick."""
    id: str
    name: str
    age: int
    gender: str
    personality: str
    energy: float
    position: dict[str, int]        # {"x": ..., "y": ...}
    inventory: dict[str, int]
    memory: list[str]               # last N memories
    internal_state: dict            # mood, goal, etc.
    nearby_agents: list[NearbyAgent]
    world_events: list[str]         # active event descriptions


class AgentAction(BaseModel):
    """Structured response the LLM must return."""
    action: str = Field(..., description="move | communicate | interact | idle | gather")
    parameters: dict = Field(default_factory=dict)
    message: str | None = Field(None, description="Optional message broadcast to nearby agents")
    memory_update: str | None = Field(None, description="One sentence to add to memory")
    internal_state: dict = Field(default_factory=dict, description="Updated mood, goal, etc.")


class AgentCreate(BaseModel):
    name: str
    age: int = 25
    gender: str = "unknown"
    personality_prompt: str = ""
    x: int | None = None
    y: int | None = None


class AgentRead(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    personality_prompt: str
    x: int
    y: int
    energy: float
    is_alive: bool
    status: str = "alive"  # alive | idle | dead
    inventory: dict
    memory: list[str]
    internal_state: dict

    model_config = {"from_attributes": True}
