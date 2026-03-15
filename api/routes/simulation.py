from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.llm import call_llm
from agents.schemas import AgentContext
from db.database import get_db
from db.models import SimulationStateModel, TickLogModel
from simulation.engine import engine

router = APIRouter(prefix="/simulation", tags=["simulation"])


class ClockStartRequest(BaseModel):
    interval_seconds: int | None = None


class SimulationStatus(BaseModel):
    current_tick: int
    is_running: bool
    tick_interval_seconds: int


@router.get("/status", response_model=SimulationStatus)
async def get_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SimulationStateModel).where(SimulationStateModel.id == 1))
    state = result.scalar_one_or_none()
    if state is None:
        return SimulationStatus(current_tick=0, is_running=False, tick_interval_seconds=30)
    return state


@router.post("/tick")
async def manual_tick():
    """Trigger a single tick immediately (dev/testing)."""
    summary = await engine.manual_tick()
    return summary


@router.post("/start")
async def start_clock(payload: ClockStartRequest = ClockStartRequest()):
    await engine.start_clock(payload.interval_seconds)
    return {"status": "started", "interval_seconds": payload.interval_seconds or 30}


@router.post("/stop")
async def stop_clock():
    await engine.stop_clock()
    return {"status": "stopped"}


@router.get("/test-llm")
async def test_llm():
    """Send a minimal test prompt to Claude and return the raw result. Use this to diagnose LLM connectivity."""
    ctx = AgentContext(
        id="test",
        name="Test",
        age=30,
        gender="unknown",
        personality="neutral",
        energy=100.0,
        position={"x": 0, "y": 0},
        inventory={},
        memory=[],
        internal_state={},
        nearby_agents=[],
        world_events=[],
    )
    action, error = await call_llm(ctx)
    return {
        "success": error is None,
        "error": error,
        "action": action.model_dump() if error is None else None,
    }


@router.get("/logs")
async def get_tick_logs(
    limit: int = 50,
    tick: int | None = None,
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(TickLogModel).order_by(TickLogModel.created_at.desc()).limit(limit)
    if tick is not None:
        query = query.where(TickLogModel.tick == tick)
    if agent_id is not None:
        query = query.where(TickLogModel.agent_id == agent_id)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "tick": log.tick,
            "agent_id": log.agent_id,
            "action": log.action,
            "parameters": log.parameters,
            "message": log.message,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
