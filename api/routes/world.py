from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import WorldEventModel
from simulation.events import PREDEFINED_EVENTS

router = APIRouter(prefix="/world", tags=["world"])


class EventCreate(BaseModel):
    event_type: str
    description: str | None = None
    data: dict = {}


class EventRead(BaseModel):
    id: str
    tick: int
    event_type: str
    description: str
    data: dict
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/events", response_model=list[EventRead])
async def list_events(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    query = select(WorldEventModel)
    if active_only:
        query = query.where(WorldEventModel.is_active == True)  # noqa: E712
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/events", response_model=EventRead, status_code=201)
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select as sel
    from db.models import SimulationStateModel

    tick_result = await db.execute(sel(SimulationStateModel).where(SimulationStateModel.id == 1))
    state = tick_result.scalar_one_or_none()
    current_tick = state.current_tick if state else 0

    description = payload.description
    if description is None:
        predefined = PREDEFINED_EVENTS.get(payload.event_type)
        if predefined:
            description = predefined.description
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown event type '{payload.event_type}'. Provide a description or use: {list(PREDEFINED_EVENTS.keys())}",
            )

    event = WorldEventModel(
        tick=current_tick,
        event_type=payload.event_type,
        description=description,
        data=payload.data,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=204)
async def deactivate_event(event_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorldEventModel).where(WorldEventModel.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_active = False
    await db.commit()


@router.get("/events/predefined")
async def list_predefined_events():
    return {k: v.description for k, v in PREDEFINED_EVENTS.items()}
