"""
WebSocket endpoint for real-time bidirectional code execution
"""

import asyncio
import json
import secrets
import time
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse


from api.services import JobService
from api.services.pubsub_service import get_pubsub_service
from api.connect.redis_manager import get_async_redis
from api.models.schema import CodeSubmission
from api.security.validator import CodeValidator
from logger.logger import log
from config.settings import get_settings
from executors import get_executor, get_default_filename


router = APIRouter()


class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[job_id] = websocket
        log.info(f"WebSocket connected for job {job_id}")

    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]
            log.info(f"WebSocket disconnected for job {job_id}")

    async def send_message(self, job_id: str, message: Dict[str, Any]):
        if job_id in self.active_connections:
            websocket = self.active_connections[job_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                log.error(f"Error sending message to job {job_id}: {str(e)}")


manager = ConnectionManager()


@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    """ websocket endpoint """

    job_id: str = None

    try:
        
        await websocket.accept()
        log.debug("WebSocket connection accepted, waiting for execute message")

        data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=5.0  # Prevent connection camping
        )

        # Websocket has custom auth here because websocket will not allow
        # for HTTP heads 
        settings = get_settings()
        client_api_key = data.get("api_key")
        
        if not client_api_key:
            await websocket.send_json({"type": "error", "message": "API key required"})
            await websocket.close(code=1008)
            return
        
        if not secrets.compare_digest(client_api_key, settings.api_key):
            await websocket.send_json({"type": "error", "message": "Invalid API key"})
            await websocket.close(code=1008)
            return

        # Extract code submission data
        code = data.get("code", "")
        language = data.get("language", "")

        # Validate submission
        if not code or not language:
            await websocket.send_json({
                "type": "error",
                "message": "Code and language are required"
            })
            await websocket.close()
            return

        try:
            executor = get_executor(language)
            # Get default filename from language config

            filename = get_default_filename(language)
        except Exception:
            filename = "main.txt"

        # Create code submission
        try:
            submission = CodeSubmission(code=code, language=language, filename=filename)
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Invalid submission: {str(e)}"
            })
            await websocket.close()
            return

        validator = CodeValidator()
        is_valid, error_message = validator.validate(submission.code, submission.language)

        if not is_valid:
            await websocket.send_json({
                "type": "error",
                "message": f"Code validation failed: {error_message}"
            })
            await websocket.close()
            return

        # Create job
        redis = await get_async_redis()
        job_service = JobService(redis)
        job_id = await job_service.create_job(
            submission.code,
            submission.language,
            submission.filename
        )

        log.info(f"Created job {job_id} for PTY streaming execution")

        # Register connection
        manager.active_connections[job_id] = websocket

        # Create input queue for bidirectional communication
        input_queue = asyncio.Queue()

        pubsub_service = get_pubsub_service()

        # Define message handler - forwards PTY output to WebSocket
        async def handle_pubsub_message(message: Dict[str, Any]):
            """Forward Pub/Sub messages to WebSocket"""
            await manager.send_message(job_id, message)

        subscription_task = asyncio.create_task(
            pubsub_service.subscribe_to_channels(job_id, handle_pubsub_message)
        )

        await redis.lpush("codr:job_queue", json.dumps({
            "job_id": job_id,
            "code": submission.code,
            "language": submission.language,
            "filename": submission.filename,
            "queued_at": time.time()
        }))
        
        log.info(f"Job {job_id} queued for worker (queue depth: {await redis.llen('codr:job_queue')})")

        # Handle incoming messages - put input directly into queue
        try:
            while True:
                message = await websocket.receive_json()

                if message.get("type") == "input":
                    input_data = message.get("data", "")
                    if len(input_data) > settings.max_input_mb:
                        log.warning(f"Input too large for job {job_id}: {len(input_data)} bytes")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Input too large (max 10KB)"
                        })
                        continue
                    await redis.publish(f"job:{job_id}:input", input_data)
                    log.debug(f"Published input to worker for job {job_id}: {input_data[:50]}")
                else:
                    log.warning(f"Unknown message type: {message.get('type')}")

        except WebSocketDisconnect:
            log.info(f"WebSocket disconnected for job {job_id}")
        except Exception as e:
            log.error(f"Error in WebSocket message loop: {_santize_error(e)}")
            await websocket.send_json({
                "type": "error",
                "message": f"WebSocket error: {str(e)}"
            })

    except WebSocketDisconnect:
        log.info("WebSocket disconnected before job creation")
    except Exception as e:
        log.error(f"WebSocket error: {_santize_error(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {_santize_error(e)}"
            })
        except:
            pass
    finally:
        # Cleanup
        if job_id:
            manager.disconnect(job_id)
            # Cancel tasks if still running
            if 'subscription_task' in locals() and not subscription_task.done():
                subscription_task.cancel()


def _santize_error(error: Exception) -> str:
    if get_settings().env == 'development':
        return str(error)
    else:
        return "An Error has occured processing your request"

@router.get("/api/websocket/status")
async def websocket_status(request: Request):
    # Status contains sensitve info, so its protected
    await verify_api_key(request)
    return JSONResponse(content={
        "active_connections": len(manager.active_connections),
        "job_ids": list(manager.active_connections.keys())
    })
