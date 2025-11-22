"""
Real-time communication between executors and WebSocket clients
"""

import json
from typing import Callable, Optional, Dict, Any, Awaitable
import redis.asyncio as aioredis
from lib.redis import get_async_redis
from lib.logger import log


class PubSubService:

    def __init__(self):
        self._pubsubs: Dict[str, aioredis.client.PubSub] = {}

    async def publish_output(self, job_id: str, stream: str, data: str):
        """
        Args:
            job_id: Job identifier
            stream: Either 'stdout' or 'stderr'
            data: Output data to publish
        """
        redis = await get_async_redis()
        channel = self._output_channel(job_id)
        message = json.dumps({"type": "output", "stream": stream, "data": data})
        await redis.publish(channel, message)
        log.debug(f"Published to {channel}: {stream}")

    async def publish_complete(
        self, job_id: str, exit_code: int, execution_time: float
    ):
        redis = await get_async_redis()
        channel = self._complete_channel(job_id)
        message = json.dumps(
            {
                "type": "complete",
                "exit_code": exit_code,
                "execution_time": execution_time,
            }
        )
        await redis.publish(channel, message)
        log.info(f"Published completion for job {job_id}")

    async def publish_error(self, job_id: str, error_message: str):
        redis = await get_async_redis()
        channel = self._output_channel(job_id)
        message = json.dumps({"type": "error", "message": error_message})
        await redis.publish(channel, message)
        log.error(f"Published error for job {job_id}: {error_message}")

    async def subscribe_to_channels(
        self, job_id: str, on_message: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Subscribe to all job-related channels and handle messages

        Args:
            job_id: Job identifier
            on_message: Async callback function to handle received messages
        """
        redis = await get_async_redis()
        pubsub = redis.pubsub()

        channels = [self._output_channel(job_id), self._complete_channel(job_id)]

        await pubsub.subscribe(*channels)
        self._pubsubs[job_id] = pubsub

        log.info(f"Subscribed to channels for job {job_id}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await on_message(data)

                        # Break the loop on job completion
                        if data.get("type") == "complete":
                            log.info(f"Job {job_id} completed, stopping subscription")
                            break
                    except json.JSONDecodeError:
                        log.error(f"Failed to decode message: {message['data']}")
                    except Exception as e:
                        log.error(f"Error handling message: {str(e)}")
        finally:
            await self.unsubscribe(job_id)

    async def unsubscribe(self, job_id: str):

        if job_id in self._pubsubs:
            pubsub = self._pubsubs[job_id]
            await pubsub.unsubscribe()
            await pubsub.close()
            del self._pubsubs[job_id]
            log.info(f"Unsubscribed from channels for job {job_id}")

    async def close(self):
        for job_id in list(self._pubsubs.keys()):
            await self.unsubscribe(job_id)

        log.info("Pub/Sub subscriptions closed")

    def _output_channel(self, job_id: str) -> str:
        return f"job:{job_id}:output"

    def _complete_channel(self, job_id: str) -> str:
        return f"job:{job_id}:complete"


# Singleton instance
_pubsub_service: Optional[PubSubService] = None


def get_pubsub_service() -> PubSubService:
    """Get or create PubSubService singleton"""
    global _pubsub_service
    if _pubsub_service is None:
        _pubsub_service = PubSubService()
    return _pubsub_service
