"""
Unified Async Redis Connection Manager

Single async Redis connection for all operations:
- Job metadata (hash operations)
- Pub/Sub messaging (real-time communication)
"""

import ssl
import redis.asyncio as aioredis
from typing import Optional
from config.settings import get_settings
from logger.logger import log


class AsyncRedisManager:

    _instance: Optional[aioredis.Redis] = None

    @classmethod
    async def get_connection(cls) -> aioredis.Redis:
        if cls._instance is None:
            settings = get_settings()
            redis_url = settings.redis_url
            env_mode = settings.env

            if not redis_url:
                if env_mode == "development":
                    redis_url = "redis://localhost:6379/"
                    log.info("Using default Redis URL (development mode)")
                else:
                    raise Exception("REDIS_URL environment variable is not set.")

            try:
                # Configure TLS/SSL for secure Redis connections (rediss://)
                connection_kwargs = {
                    "decode_responses": True,  # Automatically decode bytes to strings
                    "socket_connect_timeout": 5,
                    "socket_timeout": 5,
                    "retry_on_timeout": True,
                    "health_check_interval": 30,
                }

                # Add SSL configuration for TLS connections
                if redis_url.startswith('rediss://'):
                    connection_kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
                    connection_kwargs["ssl_check_hostname"] = True
                    log.info("Using TLS for Redis connection")

                cls._instance = await aioredis.from_url(redis_url, **connection_kwargs)

                # Test connection
                await cls._instance.ping()
                log.info("Async Redis connection established")

            except Exception as e:
                cls._instance = None
                raise Exception(f"Failed to connect to Redis: {str(e)}")

        return cls._instance

    @classmethod
    async def close_connection(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            log.info("Async Redis connection closed")


# Convenience function
async def get_async_redis() -> aioredis.Redis:
    return await AsyncRedisManager.get_connection()
