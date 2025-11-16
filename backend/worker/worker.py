"""
Standalone worker process for executing code jobs.
Runs on separate servers from WebSocket handlers.

Usage:
    python worker.py
    
Environment Variables:
    REDIS_URL - Redis connection string
    WORKER_ID - Optional worker identifier (auto-generated if not set)
"""

import asyncio
import json
import os
import signal
import time
import uuid
import queue as sync_queue
from typing import Dict, Any

# Add backend to path (same as main.py)
import sys
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.connect.redis_manager import get_async_redis
from api.services.pubsub_service import get_pubsub_service
from executors import get_executor
from logger.logger import log
from config.settings import get_settings


class CodeExecutionWorker:
    """
    Worker that polls Redis job queue and executes code.
    Designed to run independently from WebSocket servers.
    """
    
    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or os.getenv("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}")
        self.running = True
        self.current_job_id = None
        self.jobs_completed = 0
        self.jobs_failed = 0
        log.info(f"Worker {self.worker_id} initializing")
    
    async def start(self):
        """Main worker loop - blocks until shutdown"""
        log.info(f"Worker {self.worker_id} started and listening for jobs")
        redis = await get_async_redis()
        
        while self.running:
            try:
                # BRPOP blocks until job available (efficient polling)
                # Timeout after 5 seconds to check if still running
                result = await redis.brpop("codr:job_queue", timeout=5)
                
                if result:
                    queue_name, job_data_json = result
                    job_data = json.loads(job_data_json)
                    
                    # Track current job for graceful shutdown
                    self.current_job_id = job_data["job_id"]
                    
                    await self.execute_job(job_data)
                    
                    self.current_job_id = None
                else:
                    # Timeout - no jobs available
                    log.debug(f"Worker {self.worker_id} idle (queue empty)")
                    
            except asyncio.CancelledError:
                log.info(f"Worker {self.worker_id} cancelled")
                break
            except Exception as e:
                log.error(f"Worker {self.worker_id} error in main loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
        
        log.info(f"Worker {self.worker_id} stopped. Stats: {self.jobs_completed} completed, {self.jobs_failed} failed")
    
    async def execute_job(self, job_data: Dict[str, Any]):
        """
        Execute a single job and publish results via Redis Pub/Sub.
        This is the core worker logic - runs on separate server from WebSocket.
        """
        job_id = job_data["job_id"]
        code = job_data["code"]
        language = job_data["language"]
        filename = job_data["filename"]
        queued_at = job_data.get("queued_at", time.time())
        
        queue_wait_time = time.time() - queued_at
        log.info(f"Worker {self.worker_id} executing job {job_id} (waited {queue_wait_time:.2f}s in queue)")
        
        try:
            # Get executor for language
            executor = await asyncio.to_thread(get_executor, language)
            
            # Get event loop for scheduling coroutines from sync executor
            loop = asyncio.get_event_loop()
            pubsub = get_pubsub_service()
            
            input_channel = f"job:{job_id}:input"
            input_queue = asyncio.Queue()
            
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
                            input_data = message["data"].decode('utf-8')
                            await input_queue.put(input_data)
                            log.debug(f"Worker {self.worker_id} received input for {job_id}: {input_data[:50]}")
                except asyncio.CancelledError:
                    await ps.unsubscribe(input_channel)
                    await ps.close()
                    log.debug(f"Worker {self.worker_id} unsubscribed from {input_channel}")
            
            # Start input listener in background
            input_task = asyncio.create_task(input_listener())
            
            # Bridge async input queue to sync queue for executor
            sync_input_queue = sync_queue.Queue()
            
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
                        job_id,
                        "stdout",
                        data.decode('utf-8', errors='replace')
                    ),
                    loop
                )
            
            log.info(f"Worker {self.worker_id} starting execution for job {job_id}")
            result = await asyncio.to_thread(
                executor.execute,
                code=code,
                filename=filename,
                on_output=on_output,
                input_queue=sync_input_queue
            )
            
            # Cleanup
            input_task.cancel()
            bridge_task.cancel()
            
            # Publish completion event
            await pubsub.publish_complete(
                job_id,
                result["exit_code"],
                result["execution_time"]
            )
            
            self.jobs_completed += 1
            log.info(f"Worker {self.worker_id} completed job {job_id} in {result['execution_time']:.2f}s (exit code: {result['exit_code']})")
            
        except Exception as e:
            import traceback
            log.error(f"Worker {self.worker_id} failed job {job_id}: {e}")
            if get_settings().env == "development":
                traceback.print_exc()
            
            # Publish error
            await get_pubsub_service().publish_error(job_id, str(e))
            self.jobs_failed += 1
    
    def stop(self):
        """Request graceful shutdown"""
        log.info(f"Worker {self.worker_id} received shutdown signal")
        if self.current_job_id:
            log.info(f"Worker {self.worker_id} will stop after completing job {self.current_job_id}")
        self.running = False


async def main():
    """Run worker with graceful shutdown"""
    worker = CodeExecutionWorker()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        log.info(f"Received signal {sig}")
        worker.stop()
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Kill
    
    # Start worker (blocks until shutdown)
    await worker.start()


if __name__ == "__main__":
    log.info("Starting Code Execution Worker")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Worker interrupted by user")
    except Exception as e:
        log.error(f"Worker crashed: {e}")
        raise
