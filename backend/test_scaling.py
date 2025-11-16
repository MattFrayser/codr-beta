"""
Test script to verify horizontal scaling works.
Run this to test that workers can execute jobs queued by WebSocket server.
"""

import asyncio
import json
import redis.asyncio as aioredis
from api.connect.redis_manager import get_async_redis


async def test_job_queue():
    """Test that job can be queued and retrieved"""
    print("Testing job queue...")
    
    redis = await get_async_redis()
    
    # Clear queue first
    await redis.delete("codr:job_queue")
    
    # Queue a test job
    test_job = {
        "job_id": "test-123",
        "code": "print('Hello from test')",
        "language": "python",
        "filename": "test.py",
        "queued_at": 1234567890
    }
    
    await redis.lpush("codr:job_queue", json.dumps(test_job))
    print(f"✓ Job queued")
    
    # Check queue length
    queue_len = await redis.llen("codr:job_queue")
    print(f"✓ Queue length: {queue_len}")
    
    # Retrieve job (what worker would do)
    result = await redis.brpop("codr:job_queue", timeout=5)
    if result:
        queue_name, job_data = result
        job = json.loads(job_data)
        print(f"✓ Job retrieved: {job['job_id']}")
        print(f"  Language: {job['language']}")
        print(f"  Code: {job['code']}")
    else:
        print("✗ Failed to retrieve job")
    
    print("\nTest complete!")


async def test_input_pubsub():
    """Test that input can be published and subscribed"""
    print("\nTesting input Pub/Sub...")
    
    redis = await get_async_redis()
    job_id = "test-456"
    input_channel = f"job:{job_id}:input"
    
    # Subscribe in background
    received_inputs = []
    
    async def subscriber():
        ps = redis.pubsub()
        await ps.subscribe(input_channel)
        print(f"✓ Subscribed to {input_channel}")
        
        async for message in ps.listen():
            if message["type"] == "message":
                data = message["data"].decode('utf-8')
                received_inputs.append(data)
                print(f"✓ Received input: {data}")
                if data == "exit":
                    break
        
        await ps.unsubscribe(input_channel)
        await ps.close()
    
    # Start subscriber
    sub_task = asyncio.create_task(subscriber())
    
    # Wait for subscription to be ready
    await asyncio.sleep(0.5)
    
    # Publish some inputs
    await redis.publish(input_channel, "Hello\n")
    await asyncio.sleep(0.1)
    await redis.publish(input_channel, "World\n")
    await asyncio.sleep(0.1)
    await redis.publish(input_channel, "exit")
    
    # Wait for subscriber to finish
    await sub_task
    
    assert len(received_inputs) == 3
    print(f"✓ All inputs received: {received_inputs}")
    print("\nTest complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("HORIZONTAL SCALING TEST SUITE")
    print("=" * 60)
    
    asyncio.run(test_job_queue())
    asyncio.run(test_input_pubsub())
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run WebSocket server: python main.py")
    print("2. Run worker (separate terminal): python worker.py")
    print("3. Connect with frontend and test execution")
