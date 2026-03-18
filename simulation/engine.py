"""
Simulation engine: orchestrates ticks, LLM calls, and world state updates.
Supports both clock-based (APScheduler) and manual ticks.
"""
import asyncio
import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents.actions import apply_action
from agents.llm import call_llm, generate_tick_summary
from agents.memory import add_memory
from agents.schemas import AgentContext, NearbyAgent
from config import settings
from db.database import AsyncSessionLocal
from db.models import AgentModel, SimulationStateModel, TickLogModel, WorldEventModel
from simulation.world import find_nearby_agents

logger = logging.getLogger(__name__)


class SimulationEngine:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._lock = asyncio.Lock()
        self._broadcast_callbacks: list[Any] = []  # WebSocket notifiers (dict)
        self._text_callbacks: list[Any] = []        # WebSocket notifiers (plain text)
        self._last_narrative: str = ""

    # ------------------------------------------------------------------
    # Public control interface
    # ------------------------------------------------------------------

    async def start_clock(self, interval_seconds: int | None = None) -> None:
        interval = interval_seconds or settings.tick_interval_seconds
        if self._scheduler.running:
            self._scheduler.remove_all_jobs()
        else:
            self._scheduler.start()

        self._scheduler.add_job(
            self._run_tick,
            "interval",
            seconds=interval,
            id="tick_job",
            replace_existing=True,
        )
        await self._set_running(True, interval)
        logger.info("Clock-based ticks started (interval=%ds)", interval)

    async def stop_clock(self) -> None:
        if self._scheduler.running:
            self._scheduler.remove_all_jobs()
        await self._set_running(False)
        logger.info("Clock-based ticks stopped")

    async def manual_tick(self) -> dict:
        """Trigger a single tick immediately. Returns tick summary."""
        return await self._run_tick()

    def register_broadcast(self, callback) -> None:
        """Register a coroutine callback invoked after each tick with the tick summary dict."""
        self._broadcast_callbacks.append(callback)

    def register_text_broadcast(self, callback) -> None:
        """Register a coroutine callback for plain-text debug messages."""
        self._text_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Internal tick logic
    # ------------------------------------------------------------------

    async def _run_tick(self) -> dict:
        async with self._lock:
            # Transaction 1 (short): advance tick and read state, then release DB lock
            # before LLM calls so stop_clock() can always write is_running=False.
            async with AsyncSessionLocal() as db:
                tick_number = await self._advance_tick(db)
                agents = await self._load_alive_agents(db)
                active_events = await self._load_active_events(db)
                event_descriptions = [e.description for e in active_events]
                last_messages = await self._load_last_messages(db, tick_number - 1)
                await db.commit()

            await self._notify(f"[tick {tick_number}] started — {len(agents)} agent(s) alive")

            if not agents:
                return {"tick": tick_number, "agents_processed": 0, "actions": []}

            agent_dicts = [self._agent_to_dict(a) for a in agents]

            # LLM calls run here without holding the DB write lock
            await self._notify(f"[tick {tick_number}] calling LLM for {len(agent_dicts)} agent(s)…")
            raw_results = await self._process_agents(agent_dicts, event_descriptions, tick_number, last_messages)

            errors = [r for r in raw_results if r["summary"].get("llm_error")]
            ok = len(raw_results) - len(errors)
            status = f"{ok}/{len(raw_results)} responses received"
            if errors:
                status += f", {len(errors)} error(s)"
            await self._notify(f"[tick {tick_number}] {status}")

            # Transaction 2 (short): persist all agent updates and logs
            async with AsyncSessionLocal() as db:
                for r in raw_results:
                    await self._persist_agent_update(db, r["updated"])
                    if r["target_update"] is not None:
                        await self._persist_agent_update(db, r["target_update"])
                    await self._log_tick_action(db, tick_number, r["agent_id"], r["action_result"])
                await db.commit()

        results = [r["summary"] for r in raw_results]
        narrative = await generate_tick_summary(tick_number, results, self._last_narrative)
        self._last_narrative = narrative
        summary = {"tick": tick_number, "agents_processed": len(results), "actions": results, "narrative": narrative}
        await self._broadcast(summary)
        logger.info("Tick %d complete — %d agents processed", tick_number, len(results))
        return summary

    async def _process_agents(
        self,
        agent_dicts: list[dict],
        event_descriptions: list[str],
        tick: int,
        last_messages: dict[str, str],
    ) -> list[dict]:
        tasks = [
            self._process_single_agent(agent, agent_dicts, event_descriptions, tick, last_messages)
            for agent in agent_dicts
        ]
        return await asyncio.gather(*tasks)

    async def _process_single_agent(
        self,
        agent: dict,
        all_agents: list[dict],
        event_descriptions: list[str],
        tick: int,
        last_messages: dict[str, str],
    ) -> dict:
        nearby_raw = find_nearby_agents(agent["id"], agent["x"], agent["y"], all_agents)
        nearby = [
            NearbyAgent(
                id=a["id"],
                name=a["name"],
                distance=a["distance"],
                last_message=last_messages.get(a["id"]),
            )
            for a in nearby_raw
        ]

        ctx = AgentContext(
            id=agent["id"],
            name=agent["name"],
            age=agent["age"],
            gender=agent["gender"],
            personality=agent["personality_prompt"],
            energy=agent["energy"],
            position={"x": agent["x"], "y": agent["y"]},
            inventory=agent["inventory"] or {},
            memory=agent["memory"] or [],
            internal_state=agent["internal_state"] or {},
            nearby_agents=nearby,
            world_events=event_descriptions,
        )

        action_result, llm_error = await call_llm(ctx)
        updated, target_update = apply_action(
            agent, action_result.action, action_result.parameters, all_agents
        )
        updated["memory"] = add_memory(agent["memory"] or [], action_result.memory_update)
        updated["internal_state"] = action_result.internal_state or agent["internal_state"]

        # Set status: dead takes priority, then idle if LLM failed, else alive
        if not updated["is_alive"]:
            updated["status"] = "dead"
        elif llm_error:
            updated["status"] = "idle"
        else:
            updated["status"] = "alive"

        return {
            "agent_id": agent["id"],
            "updated": updated,
            "target_update": target_update,
            "action_result": action_result,
            "summary": {
                "agent_id": agent["id"],
                "agent_name": agent["name"],
                "x": updated["x"],
                "y": updated["y"],
                "energy": updated["energy"],
                "is_alive": updated["is_alive"],
                "status": updated["status"],
                "action": action_result.action,
                "parameters": action_result.parameters,
                "message": action_result.message,
                "llm_error": llm_error,
            },
        }

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _advance_tick(self, db: AsyncSession) -> int:
        result = await db.execute(select(SimulationStateModel).where(SimulationStateModel.id == 1))
        state = result.scalar_one_or_none()
        if state is None:
            state = SimulationStateModel(id=1, current_tick=1)
            db.add(state)
        else:
            state.current_tick += 1
        await db.flush()
        return state.current_tick

    async def _load_alive_agents(self, db: AsyncSession) -> list[AgentModel]:
        result = await db.execute(select(AgentModel).where(AgentModel.is_alive == True))  # noqa: E712
        return list(result.scalars().all())

    async def _load_active_events(self, db: AsyncSession) -> list[WorldEventModel]:
        result = await db.execute(select(WorldEventModel).where(WorldEventModel.is_active == True))  # noqa: E712
        return list(result.scalars().all())

    async def _persist_agent_update(self, db: AsyncSession, data: dict) -> None:
        await db.execute(
            update(AgentModel)
            .where(AgentModel.id == data["id"])
            .values(
                x=data["x"],
                y=data["y"],
                energy=data["energy"],
                is_alive=data["is_alive"],
                status=data.get("status", "alive"),
                inventory=data["inventory"],
                memory=data["memory"],
                internal_state=data["internal_state"],
            )
        )

    async def _log_tick_action(
        self, db: AsyncSession, tick: int, agent_id: str, action_result
    ) -> None:
        # For communicate actions, use the content as the logged message so the
        # target agent sees it next tick via last_messages.
        message = action_result.message
        if action_result.action == "communicate" and not message:
            message = action_result.parameters.get("content")
        db.add(
            TickLogModel(
                tick=tick,
                agent_id=agent_id,
                action=action_result.action,
                parameters=action_result.parameters,
                message=message,
            )
        )

    async def _load_last_messages(self, db: AsyncSession, tick: int) -> dict[str, str]:
        """Return {agent_id: message} for all agents that sent a message in the given tick."""
        if tick < 1:
            return {}
        result = await db.execute(
            select(TickLogModel.agent_id, TickLogModel.message)
            .where(TickLogModel.tick == tick)
            .where(TickLogModel.message.isnot(None))
        )
        return {agent_id: message for agent_id, message in result.all()}

    async def _set_running(self, running: bool, interval: int | None = None) -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SimulationStateModel).where(SimulationStateModel.id == 1))
            state = result.scalar_one_or_none()
            if state is None:
                state = SimulationStateModel(id=1, is_running=running)
                if interval:
                    state.tick_interval_seconds = interval
                db.add(state)
            else:
                state.is_running = running
                if interval:
                    state.tick_interval_seconds = interval
            await db.commit()

    async def _broadcast(self, summary: dict) -> None:
        for cb in self._broadcast_callbacks:
            try:
                await cb(summary)
            except Exception as exc:
                logger.warning("Broadcast callback failed: %s", exc)

    async def _notify(self, text: str) -> None:
        """Send a plain-text debug message to all registered text listeners."""
        for cb in self._text_callbacks:
            try:
                await cb(text)
            except Exception as exc:
                logger.warning("Text broadcast failed: %s", exc)

    @staticmethod
    def _agent_to_dict(agent: AgentModel) -> dict:
        return {
            "id": agent.id,
            "name": agent.name,
            "age": agent.age,
            "gender": agent.gender,
            "personality_prompt": agent.personality_prompt,
            "x": agent.x,
            "y": agent.y,
            "energy": agent.energy,
            "is_alive": agent.is_alive,
            "status": agent.status or "alive",
            "inventory": agent.inventory or {},
            "memory": agent.memory or [],
            "internal_state": agent.internal_state or {},
        }


# Singleton — imported by routes and websocket handler
engine = SimulationEngine()
