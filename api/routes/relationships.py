"""REST endpoints for inspecting the agent relationship graph."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import AgentModel, RelationshipModel
from db.relationships import get_relationships_from

router = APIRouter(prefix="/relationships", tags=["relationships"])


class RelationshipOut(BaseModel):
    id: str
    from_agent_id: str
    to_agent_id: str
    type: str
    sub_role: str | None
    strength: float
    is_family: bool
    interaction_count: int

    model_config = {"from_attributes": True}


@router.get("/agent/{agent_id}", response_model=list[RelationshipOut])
async def get_agent_relationships(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Return all outgoing relationships for a given agent."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await get_relationships_from(db, agent_id)


@router.get("/", response_model=list[RelationshipOut])
async def list_all_relationships(db: AsyncSession = Depends(get_db)):
    """Return the full relationship graph (all edges)."""
    result = await db.execute(select(RelationshipModel))
    return list(result.scalars().all())
