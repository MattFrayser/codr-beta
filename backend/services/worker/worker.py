"""
Polls Redis queue and executes code jobs in isolated sandboxes
"""

import asyncio
import json
import time
import uuid
import os
from typing import Dict, Any, Optional
import queue as sync_queue

from lib.logger import log
from lib.config import get_settings
from lib.redis import get_async_redis
from lib.services.pubsub_service import get_pubsub_service
from lib.executors import get_executor


class CodeExecutionWorker:

    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or os.getenv(
            "WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}"
        )
        self.running = True
        self.current_job_id = None
        self.jobs_completed = 0
        self.jobs_failed = 0
        self.settings = get_settings()

        log.debug(f"Worker {self.worker_id} initializing")

    async def start(self):

        log.info(f"Worker {self.worker_id} started and listening for jobs")
        redis = await get_async_redis()

        while self.running:
            try:
                result = await redis.brpop(
                    self.settings.job_queue_name,
                    timeout=self.settings.worker_poll_timeout,
                )

                if result:
                    queue_name, job_data_json = result
                    job_data = json.loads(job_data_json)

                    # Track current job for graceful shutdown
                    self.current_job_id = job_data["job_id"]

                    # Execute the job
                    await self.execute_job(job_data)

                    self.current_job_id = None
                else:
                    # Timeout - no jobs available (normal when queue is empty)
                    pass

            except asyncio.CancelledError:
                log.info(f"Worker {self.worker_id} cancelled")
                break
            except (ConnectionError, asyncio.TimeoutError) as e:
                # Redis connection issues or timeouts - don't spam logs
                log.debug(f"Worker {self.worker_id} connection issue: {e}")
                await asyncio.sleep(1)

        log.info(
            f'''Worker {self.worker_id} stopped. Stats: {self.jobs_completed}
                completed, {self.jobs_failed} failed'''
        )

    async def execute_job(self, job_data: Dict[str, Any]):

        job_id = job_data["job_id"]
        code = job_data["code"]
        language = job_data["language"]
        filename = job_data["filename"]
        queued_at = job_data.get("queued_at", time.time())

        queue_wait_time = time.time() - queued_at
        log.info(
            f'''Worker {self.worker_id} executing job {job_id}
                (waited {queue_wait_time:.2f}s in queue)'''
        )

        try:
            executor = await asyncio.to_thread(get_executor, language)

            # Get event loop for scheduling coroutines from sync executor
            loop = asyncio.get_event_loop()
            pubsub = get_pubsub_service()

            input_channel = f"job:{job_id}:input"
            input_queue: asyncio.Queue[str] = asyncio.Queue()

            async def input_listener():
                """
                Listen for user input from WebSocket server via Redis Pub/Sub.
                Runs in background while job executes.
                """
                redis = await get_async_redis()
                ps = redis.pubsub()
                await ps.subscribe(input_channel)

                log.debug(f"Worker {self.worker_id} subscribed to {input_channel}")

                try:
                    async for message in ps.listen():
                        if message["type"] == "message":
                            input_data = message["data"]  # Current redis uses strings
                            await input_queue.put(input_data)
                            log.debug(
                                f'''Worker {self.worker_id} received
                                    input for {job_id}: {input_data[:50]}'''
                            )
                except asyncio.CancelledError:
                    await ps.unsubscribe(input_channel)
                    await ps.close()
                    log.debug(
                        f"Worker {self.worker_id} unsubscribed from {input_channel}"
                    )

            # Start input listener in background
            input_task = asyncio.create_task(input_listener())

            # Bridge async input queue to sync queue for executor
            sync_input_queue: sync_queue.Queue[str] = sync_queue.Queue()

            async def bridge_input():
                """Transfer items from async queue to sync queue"""
                try:
                    while True:
                        item = await input_queue.get()
                        sync_input_queue.put(item)
                except asyncio.CancelledError:
                    pass

            bridge_task = asyncio.create_task(bridge_input())

            # Callback for output streaming
            def on_output(data: bytes):
                """
                Called when PTY produces output.
                Publishes to Redis Pub/Sub for WebSocket server to receive.
                """
                asyncio.run_coroutine_threadsafe(
                    pubsub.publish_output(
                        job_id, "stdout", data.decode("utf-8", errors="replace")
                    ),
                    loop,
                )

            # Execute code in sandboxed environment
            log.info(f"Worker {self.worker_id} starting execution for job {job_id}")
            result = await asyncio.to_thread(
                executor.execute,
                code=code,
                filename=filename,
                on_output=on_output,
                input_queue=sync_input_queue,
            )

            # Cleanup
            input_task.cancel()
            bridge_task.cancel()

            # Publish completion event
            await pubsub.publish_complete(
                job_id, result.exit_code, result.execution_time
            )

            self.jobs_completed += 1
            log.info(
                f'''Worker {self.worker_id} completed job {job_id} in
                 {result.execution_time:.2f}s (exit code: {result.exit_code})'''
            )
        except Exception as e:
            import traceback

            log.error(f"Worker {self.worker_id} failed job {job_id}: {e}")
            if self.settings.env == "development":
                traceback.print_exc()

            # Publish error
            await get_pubsub_service().publish_error(job_id, str(e))
            self.jobs_failed += 1

    def stop(self):
        """
        Request graceful shutdown

        If a job is currently executing, it will complete before stopping.
        """
        log.info(f"Worker {self.worker_id} received shutdown signal")
        if self.current_job_id:
            log.info(
                f'''Worker {self.worker_id} will stop after completing job
                {self.current_job_id}'''
            )
        self.running = False
