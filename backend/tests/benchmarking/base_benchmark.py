import asyncio
import json
import os
import time
import websockets
import requests


class BaseBenchmark:
    """Base class for benchmark tests with shared functionality"""

    # Test code samples
    FIBONACCI_TEST = (
        "def fibonacci(n):\n"
        "    if n <= 1: return n\n"
        "    return fibonacci(n-1) + fibonacci(n-2)\n"
        "print(fibonacci(20))"
    )

    def __init__(self, api_key=None, base_url=None):
        """Initialize with configuration from environment or defaults"""
        self.api_key = api_key or os.environ.get("API_KEY", "dev-secret-key-123")
        self.base_url = base_url or os.environ.get("BASE_URL", "http://localhost:8000")
        self.ws_url = os.environ.get(
            "WS_URL",
            self.base_url.replace("http", "ws") + "/ws/execute"
        )

    def create_job(self):
        """Create a new job via REST API"""
        resp = requests.post(
            f"{self.base_url}/api/jobs/create",
            headers={"X-API-Key": self.api_key}
        )
        return resp.json()

    async def execute_job_via_websocket(self, job_id, job_token, code, language="python"):
        """Execute a job via WebSocket and wait for completion"""
        async with websockets.connect(self.ws_url) as ws:
            await ws.send(json.dumps({
                "type": "execute",
                "job_id": job_id,
                "job_token": job_token,
                "code": code,
                "language": language
            }))

            while True:
                msg = json.loads(await ws.recv())
                msg_type = msg.get("type")

                if msg_type == "complete":
                    return True
                elif msg_type == "error":
                    return False

    async def run_job_with_timing(self, code=None, language="python"):
        """Run a single job and return elapsed time"""
        code = code or self.FIBONACCI_TEST
        start = time.time()

        job = self.create_job()
        await self.execute_job_via_websocket(
            job["job_id"],
            job["job_token"],
            code,
            language
        )

        return time.time() - start

    async def run_job_with_result(self, code=None, language="python"):
        """Run a single job and return success/failure"""
        code = code or self.FIBONACCI_TEST

        job = self.create_job()
        result = await self.execute_job_via_websocket(
            job["job_id"],
            job["job_token"],
            code,
            language
        )

        return result

    async def run_batch(self, total_jobs, concurrency, job_runner, progress_callback=None):
        """
        Execute jobs in batches with configurable concurrency

        Args:
            total_jobs: Total number of jobs to run
            concurrency: Number of concurrent jobs per batch
            job_runner: Async function that runs a single job
            progress_callback: Optional callback for progress updates (current, total)

        Returns:
            List of results from all jobs
        """
        all_results = []

        for i in range(0, total_jobs, concurrency):
            batch = min(concurrency, total_jobs - i)
            tasks = [job_runner() for _ in range(batch)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(results)

            current = i + batch
            if progress_callback:
                progress_callback(current, total_jobs)
            else:
                print(f"Progress: {current}/{total_jobs}")

        return all_results

    def print_header(self, title):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}\n")

    def calculate_success_rate(self, results):
        """Calculate success and failure counts from results"""
        success = sum(1 for r in results if not isinstance(r, Exception) and r)
        failed = len(results) - success
        return success, failed
