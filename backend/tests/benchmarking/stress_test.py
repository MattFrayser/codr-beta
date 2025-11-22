import asyncio
import argparse
import time
from base_benchmark import BaseBenchmark


class StressTest(BaseBenchmark):
    """Stress test for high concurrency scenarios"""

    def __init__(self, api_key=None, base_url=None):
        super().__init__(api_key, base_url)

    async def run_stress_test(self, total_jobs=1000, concurrent=100):
        """Run stress test with high concurrency"""
        self.print_header(f"STRESS TEST: {total_jobs} jobs, {concurrent} concurrent")

        start = time.time()
        results = await self.run_batch(
            total_jobs,
            concurrent,
            self.run_job_with_result
        )

        # Count results
        completed = 0
        failed = 0
        for r in results:
            if isinstance(r, Exception):
                failed += 1
            elif r:
                completed += 1
            else:
                failed += 1

        elapsed = time.time() - start
        rate = total_jobs / elapsed

        print(f"\nCompleted: {completed}/{total_jobs}")
        print(f"Failed: {failed}/{total_jobs}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {rate:.2f} jobs/sec")

        return rate


async def main():
    parser = argparse.ArgumentParser(description='Run stress test with configurable parameters')
    parser.add_argument(
        '--jobs', '-j',
        type=int,
        default=1000,
        help='Total number of jobs to run (default: 1000)'
    )
    parser.add_argument(
        '--concurrent', '-c',
        type=int,
        default=100,
        help='Number of concurrent jobs (default: 100)'
    )

    args = parser.parse_args()

    # Configuration loaded from environment variables or defaults
    stress = StressTest()
    await stress.run_stress_test(total_jobs=args.jobs, concurrent=args.concurrent)


if __name__ == "__main__":
    asyncio.run(main())
