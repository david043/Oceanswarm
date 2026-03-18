import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class AgentModel(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, default=25)
    gender: Mapped[str] = mapped_column(String, default="unknown")
    personality_prompt: Mapped[str] = mapped_column(Text, default="")

    # Position on the world grid
    x: Mapped[int] = mapped_column(Integer, default=0)
    y: Mapped[int] = mapped_column(Integer, default=0)

    # Vitals
    energy: Mapped[float] = mapped_column(Float, default=100.0)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String, default="alive")  # alive | idle | dead

    # JSON fields
    inventory: Mapped[dict] = mapped_column(JSON, default=dict)
    memory: Mapped[list] = mapped_column(JSON, default=list)        # last N memories
    internal_state: Mapped[dict] = mapped_column(JSON, default=dict) # mood, goal, etc.

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WorldEventModel(Base):
    __tablename__ = "world_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tick: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "market_crash", "storm"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SimulationStateModel(Base):
    __tablename__ = "simulation_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    current_tick: Mapped[int] = mapped_column(Integer, default=0)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)
    tick_interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TickLogModel(Base):
    __tablename__ = "tick_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tick: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
