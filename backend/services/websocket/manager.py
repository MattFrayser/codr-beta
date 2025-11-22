"""
Manages active WebSocket connections and message broadcasting
"""

from typing import Dict, Any
from fastapi import WebSocket
from lib.logger import log


class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    def register(self, job_id: str, websocket: WebSocket) -> None:
        self.active_connections[job_id] = websocket
        log.info(f"WebSocket registered for job {job_id}")

    def disconnect(self, job_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            job_id: Job identifier to disconnect
        """
        if job_id in self.active_connections:
            del self.active_connections[job_id]
            log.info(f"WebSocket disconnected for job {job_id}")

    async def send_message(self, job_id: str, message: Dict[str, Any]) -> None:
        """
        Send a message to a specific WebSocket connection.
        """
        if job_id in self.active_connections:
            websocket = self.active_connections[job_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                log.error(f"Error sending message to job {job_id}: {str(e)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all active connections.
        """
        for job_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                log.error(f"Error broadcasting to job {job_id}: {str(e)}")

    def connection_count(self) -> int:
        return len(self.active_connections)

    def get_job_ids(self) -> list:
        return list(self.active_connections.keys())

    def is_connected(self, job_id: str) -> bool:
        """Check if a job has an active connection"""
        return job_id in self.active_connections
