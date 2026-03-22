"""WebSocket endpoint: streams tick summaries to connected clients."""
import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from simulation.formatting import format_tick_summary

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket client connected (%d total)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections = [c for c in self._connections if c is not ws]
        logger.info("WebSocket client disconnected (%d remaining)", len(self._connections))

    async def broadcast(self, data: dict) -> None:
        await self.broadcast_text(format_tick_summary(data))

    async def broadcast_text(self, text: str) -> None:
        async with self._lock:
            targets = list(self._connections)
        dead = []
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; all data is server-pushed via broadcast
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
