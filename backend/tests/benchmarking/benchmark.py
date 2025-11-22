import asyncio
import time
import statistics
import os
from base_benchmark import BaseBenchmark


class Benchmark(BaseBenchmark):
    def __init__(self, api_key=None, base_url=None):
        super().__init__(api_key, base_url)
     
    async def benchmark_throughput(self, total_jobs=100, concurrency=10):
        """Measure jobs per second"""
        self.print_header(f"THROUGHPUT TEST: {total_jobs} jobs, {concurrency} concurrent")

        start_time = time.time()
        results = await self.run_batch(
            total_jobs,
            concurrency,
            self.run_job_with_timing
        )

        success = sum(1 for r in results if not isinstance(r, Exception))
        elapsed = time.time() - start_time
        throughput = total_jobs / elapsed

        print(f"\nCompleted: {success}/{total_jobs}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Throughput: {throughput:.2f} jobs/sec")

        return throughput
    
    async def benchmark_latency(self, samples=20):
        """Measure response time"""
        self.print_header(f"LATENCY TEST: {samples} samples")

        latencies = []
        for i in range(samples):
            try:
                latency = await self.run_job_with_timing()
                latencies.append(latency * 1000)  # Convert to ms
                print(f"Sample {i+1}: {latency*1000:.0f}ms")
            except Exception as e:
                print(f"Sample {i+1} failed: {e}")

        if latencies:
            print(f"\nMin:    {min(latencies):.0f}ms")
            print(f"Max:    {max(latencies):.0f}ms")
            print(f"Mean:   {statistics.mean(latencies):.0f}ms")
            print(f"Median: {statistics.median(latencies):.0f}ms")

        return statistics.mean(latencies) if latencies else 0

async def main():
    # Configuration loaded from environment variables or defaults
    bench = Benchmark()

    # Run benchmarks
    await bench.benchmark_latency(samples=20)
    await bench.benchmark_throughput(total_jobs=100, concurrency=10)

if __name__ == "__main__":
    asyncio.run(main())

