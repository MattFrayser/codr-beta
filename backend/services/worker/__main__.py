"""
Worker Service Entry Point
Starts the code execution worker process
"""

import asyncio
import signal
from lib.logger import log
from lib.config import get_settings
from .worker import CodeExecutionWorker


def setup_signal_handlers(worker: CodeExecutionWorker):
    """Configure graceful shutdown on SIGINT/SIGTERM"""

    def signal_handler(sig, frame):
        signal_name = signal.Signals(sig).name
        log.info(f"Received signal {signal_name}")
        worker.stop()

    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Kill


async def main():

    settings = get_settings()

    # Validate configuration
    if not settings.redis_url:
        log.error("REDIS_URL not configured")
        sys.exit(1)

    # Create worker
    worker = CodeExecutionWorker()

    # Setup signal handlers for graceful shutdown
    setup_signal_handlers(worker)

    # Start worker (blocks until shutdown signal)
    try:
        await worker.start()
    except Exception as e:
        log.error(f"Worker crashed: {e}")
        raise
    finally:
        log.info("Worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Worker interrupted by user")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        sys.exit(1)
