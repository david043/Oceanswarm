"""CRUD helpers for the agent relationship graph."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RelationshipModel

# Relationship types the LLM is allowed to form or end dynamically
DYNAMIC_TYPES = frozenset(
    {"friend", "enemy", "ally", "rival", "mentor", "leader", "business_partner"}
)

# Strength adjustment applied automatically by each interaction type
INTERACTION_STRENGTH_DELTA: dict[str, float] = {
    "fight": -15.0,
    "help": 8.0,
    "trade": 5.0,
}


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


async def get_relationships_from(
    db: AsyncSession, from_agent_id: str
) -> list[RelationshipModel]:
    """Return all outgoing relationships for an agent."""
    result = await db.execute(
        select(RelationshipModel).where(RelationshipModel.from_agent_id == from_agent_id)
    )
    return list(result.scalars().all())


async def get_relationships_for_agents(
    db: AsyncSession, agent_ids: list[str]
) -> list[RelationshipModel]:
    """Return all outgoing relationships whose source is in agent_ids (single query)."""
    if not agent_ids:
        return []
    result = await db.execute(
        select(RelationshipModel).where(RelationshipModel.from_agent_id.in_(agent_ids))
    )
    return list(result.scalars().all())


async def get_relationship(
    db: AsyncSession, from_id: str, to_id: str, rel_type: str
) -> RelationshipModel | None:
    result = await db.execute(
        select(RelationshipModel).where(
            RelationshipModel.from_agent_id == from_id,
            RelationshipModel.to_agent_id == to_id,
            RelationshipModel.type == rel_type,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


async def create_family_link(
    db: AsyncSession,
    from_agent_id: str,
    to_agent_id: str,
    rel_type: str,          # "family" | "mate"
    sub_role: str | None,   # "parent_of" | "child_of" | "sibling_of" | None
    initial_strength: float = 70.0,
) -> RelationshipModel:
    """Create an immutable family/mate relationship. Caller must commit."""
    rel = RelationshipModel(
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        type=rel_type,
        sub_role=sub_role,
        strength=initial_strength,
        is_family=True,
    )
    db.add(rel)
    return rel


async def form_relationship(
    db: AsyncSession,
    from_agent_id: str,
    to_agent_id: str,
    rel_type: str,
    initial_strength: float = 20.0,
) -> RelationshipModel | None:
    """
    Create a new dynamic relationship if it does not already exist.
    Returns None (and does nothing) if the type is not in DYNAMIC_TYPES.
    Caller must commit.
    """
    if rel_type not in DYNAMIC_TYPES:
        return None

    existing = await get_relationship(db, from_agent_id, to_agent_id, rel_type)
    if existing is not None:
        return existing  # already exists — no duplicate

    rel = RelationshipModel(
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        type=rel_type,
        strength=initial_strength,
        is_family=False,
    )
    db.add(rel)
    return rel


async def end_relationship(
    db: AsyncSession, from_agent_id: str, to_agent_id: str, rel_type: str
) -> bool:
    """
    Delete a dynamic relationship.  Family relationships are never deleted.
    Returns True if a row was removed.
    """
    existing = await get_relationship(db, from_agent_id, to_agent_id, rel_type)
    if existing is None or existing.is_family:
        return False
    await db.execute(
        delete(RelationshipModel).where(RelationshipModel.id == existing.id)
    )
    return True


async def adjust_strength(
    db: AsyncSession,
    from_agent_id: str,
    to_agent_id: str,
    delta: float,
) -> None:
    """
    Shift the strength of *all* existing (non-family) relationships between
    from → to by delta, clamping to [-100, +100].

    For fights specifically, if there is no existing relationship a weak
    "enemy" edge is auto-created.
    Caller must commit.
    """
    result = await db.execute(
        select(RelationshipModel).where(
            RelationshipModel.from_agent_id == from_agent_id,
            RelationshipModel.to_agent_id == to_agent_id,
        )
    )
    rels = list(result.scalars().all())

    if not rels and delta < 0:
        # Fight with no prior relationship → auto-create enemy
        enemy = RelationshipModel(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            type="enemy",
            strength=max(-100.0, delta),
            is_family=False,
            interaction_count=1,
        )
        db.add(enemy)
        return

    for rel in rels:
        rel.strength = max(-100.0, min(100.0, rel.strength + delta))
        rel.interaction_count += 1
