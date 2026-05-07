from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info(f"WebSocket connected for project {project_id}. Active connections: {len(self.active_connections[project_id])}")

    def disconnect(self, websocket: WebSocket, project_id: int):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)

    async def broadcast(self, message: dict, project_id: int):
        if project_id in self.active_connections:
            logger.info(f"Broadcasting to {len(self.active_connections[project_id])} clients for project {project_id}: {message.get('status')}")
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to project {project_id}: {e}")
                    continue
        else:
            logger.warning(f"No active WebSocket connections for project {project_id} to receive broadcast: {message.get('status')}")

manager = ConnectionManager()
