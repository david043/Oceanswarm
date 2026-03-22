"""Pydantic schemas for agent data flowing in and out of the system."""
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Relationship schemas
# ---------------------------------------------------------------------------

class RelationshipSummary(BaseModel):
    """Relationship from this agent's perspective toward a nearby agent."""
    type: str                # e.g. "friend", "family", "enemy"
    sub_role: str | None     # "parent_of" | "child_of" | "sibling_of" (family only)
    strength: float          # -100 … +100
    label: str               # human-readable, e.g. "your mother", "a trusted ally"


class RelationshipUpdate(BaseModel):
    """
    Explicit relationship change the LLM can request.
    Only dynamic types (friend, enemy, ally, rival, mentor, leader,
    business_partner) are accepted; family/mate are immutable.
    """
    action: str    # "form" | "end"
    target_id: str
    type: str      # relationship type to form or end


class FamilyLink(BaseModel):
    """
    Family or mate link provided at agent creation time.
    role must be one of: parent_of | child_of | sibling_of | mate
    """
    agent_id: str
    role: str  # "parent_of" | "child_of" | "sibling_of" | "mate"


# ---------------------------------------------------------------------------
# Nearby agent context
# ---------------------------------------------------------------------------

class NearbyAgent(BaseModel):
    id: str
    name: str
    distance: float
    last_message: str | None = None
    relationship: RelationshipSummary | None = None


# ---------------------------------------------------------------------------
# Full context passed to the LLM each tick
# ---------------------------------------------------------------------------

class AgentContext(BaseModel):
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


# ---------------------------------------------------------------------------
# Structured response the LLM must return
# ---------------------------------------------------------------------------

class AgentAction(BaseModel):
    action: str = Field(..., description="move | communicate | interact | idle | gather")
    parameters: dict = Field(default_factory=dict)
    message: str | None = Field(None, description="Optional message broadcast to nearby agents")
    memory_update: str | None = Field(None, description="One sentence to add to memory")
    internal_state: dict = Field(default_factory=dict, description="Updated mood, goal, etc.")
    relationship_update: RelationshipUpdate | None = Field(
        None,
        description=(
            "Optional: form or end a dynamic relationship with a nearby agent. "
            'Use {"action": "form", "type": "friend", "target_id": "..."} or '
            '{"action": "end", "type": "friend", "target_id": "..."}. '
            "Family/mate bonds cannot be changed."
        ),
    )


# ---------------------------------------------------------------------------
# REST API schemas
# ---------------------------------------------------------------------------

class AgentCreate(BaseModel):
    name: str
    age: int = 25
    gender: str = "unknown"
    personality_prompt: str = ""
    x: int | None = None
    y: int | None = None
    family_links: list[FamilyLink] = Field(
        default_factory=list,
        description=(
            "Family or mate relationships to establish at creation. "
            "Roles: parent_of | child_of | sibling_of | mate. "
            "These are immutable — they cannot be changed after creation."
        ),
    )


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
