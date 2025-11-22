"""
Handles creation, retrieval, and status updates for code execution jobs.

Responsibilities:
- Create new jobs with unique IDs
- Track job status (queued → processing → completed/failed)
- Store and retrieve execution results
- Provide job metadata

Architecture:
- Redis Hash: Job metadata storage (job:{job_id})
"""

import uuid
import time
import json
import redis.asyncio as aioredis
from typing import Optional
from lib.models import JobResult
from lib.config import get_settings


class JobService:

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.settings = get_settings()

    def _job_key(self, job_id: str) -> str:
        return f"job:{job_id}"

    async def create_job(self, code: str, language: str, filename: str) -> str:

        job_id = str(uuid.uuid4())
        created_at = str(time.time())

        job_data = {
            "job_id": job_id,
            "code": code,
            "language": language,
            "filename": filename,
            "status": "queued",
            "created_at": created_at,
        }

        job_key = self._job_key(job_id)
        await self.redis.hset(job_key, mapping=job_data)  # type: ignore[misc]

        # Set TTL on job metadata
        await self.redis.expire(job_key, self.settings.redis_ttl)

        return job_id

    async def get_job(self, job_id: str) -> Optional[JobResult]:
        """
        Returns:
            JobResult model or None if not found
        """
        job_key = self._job_key(job_id)
        job_data = await self.redis.hgetall(job_key)  # type: ignore[misc]

        if not job_data:
            return None

        result = job_data.get("result")
        if result:
            try:
                job_data["result"] = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass

        return JobResult(**job_data)

    async def mark_processing(self, job_id: str) -> None:
        job_key = self._job_key(job_id)
        await self.redis.hset(job_key, "status", "processing")  # type: ignore[misc]

    async def mark_completed(self, job_id: str, result: dict) -> None:
        job_key = self._job_key(job_id)
        completed_at = str(time.time())

        # Update multiple fields atomically using pipeline
        pipe = self.redis.pipeline()
        pipe.hset(job_key, "result", json.dumps(result))
        pipe.hset(job_key, "status", "completed")
        pipe.hset(job_key, "completed_at", completed_at)
        await pipe.execute()

    async def mark_failed(self, job_id: str, error: str, result: Optional[dict] = None) -> None:
        job_key = self._job_key(job_id)

        pipe = self.redis.pipeline()
        pipe.hset(job_key, "error", error)
        pipe.hset(job_key, "status", "failed")

        if result:
            pipe.hset(job_key, "result", json.dumps(result))

        await pipe.execute()

    async def job_exists(self, job_id: str) -> bool:
        job_key = self._job_key(job_id)
        return await self.redis.exists(job_key) > 0

    async def get_job_status(self, job_id: str) -> Optional[str]:
        job_key = self._job_key(job_id)
        status = await self.redis.hget(job_key, "status")  # type: ignore[misc]

        return status if status else None
