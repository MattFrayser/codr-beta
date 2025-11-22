"""
WebSocket endpoint for real-time bidirectional code execution
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .manager import ConnectionManager
from lib.services import JobService
from lib.services.pubsub_service import get_pubsub_service
from lib.redis import get_async_redis
from lib.models.schema import CodeSubmission
from lib.security.validator import CodeValidator
from .middleware.jwt_manager import get_token_manager
from lib.logger import log
from lib.config import get_settings
from .middleware import verify_api_key
from lib.executors import get_default_filename

router = APIRouter()
manager = ConnectionManager()


# Request/Response models for job creation
class CreateJobRequest(BaseModel):
    """Request model for job creation (optional, for future use)."""

    # Can add fields like: max_execution_time, language_filter, etc.
    pass


class CreateJobResponse(BaseModel):
    """Response model for job creation."""

    job_id: str
    job_token: str
    expires_at: str


@router.post("/api/jobs/create", response_model=CreateJobResponse)
async def create_job(
    request: Optional[CreateJobRequest] = None,
    _: bool = Depends(verify_api_key),  # Require API key for job creation
):
    """
    Create a new code execution job.

    This endpoint requires API key authentication via X-API-Key header.
    Returns a job_id and short-lived job_token for WebSocket authentication.

    Security:
    - API key required (prevents unauthorized job creation)
    - Job token expires in 15 minutes
    - Job token can only be used once (single-use)
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Create signed JWT token
    token_manager = get_token_manager()
    token_data = token_manager.create_job_token(job_id)

    log.info(f"Created job {job_id} with token (expires: {token_data['expires_at']})")

    return CreateJobResponse(**token_data)


@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    """
    WebSocket endpoint for code execution.

    Authentication:
    - First message must contain: {type: 'execute', job_id, job_token, code, language}
    - job_token is verified before any code execution
    - Tokens are single-use and expire after 15 minutes
    """

    job_id: Optional[str] = None

    try:

        await websocket.accept()
        log.debug("WebSocket connection accepted, waiting for execute message")

        data = await asyncio.wait_for(
            websocket.receive_json(), timeout=5.0  # Prevent connection camping
        )

        # Extract authentication fields (JWT token replaces API key)
        job_id = data.get("job_id")
        job_token = data.get("job_token")

        if not job_id or not job_token:
            await websocket.send_json(
                {"type": "error", "message": "Missing job_id or job_token"}
            )
            await websocket.close(code=1008)
            return

        # Verify JWT token
        token_manager = get_token_manager()
        try:
            payload = token_manager.verify_job_token(job_token, job_id)
            jti = payload.get("jti")

            if not jti:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid token: missing JTI"}
                )
                await websocket.close(code=1008)
                return

            # Check if token already used (single-use enforcement)
            if await token_manager.is_token_used(jti):
                await websocket.send_json(
                    {"type": "error", "message": "Job token has already been used"}
                )
                await websocket.close(code=1008)
                return

            # Mark token as used
            await token_manager.mark_token_used(jti)

            log.info(f"Job {job_id} authenticated successfully")

        except Exception as e:
            log.warning(f"Job {job_id} authentication failed: {str(e)}")
            await websocket.send_json(
                {"type": "error", "message": "Authentication failed"}
            )
            await websocket.close(code=1008)
            return

        # Extract code submission data
        code = data.get("code", "")
        language = data.get("language", "")

        # Validate submission
        if not code or not language:
            await websocket.send_json(
                {"type": "error", "message": "Code and language are required"}
            )
            await websocket.close()
            return

        filename = get_default_filename(language)

        # Create code submission
        try:
            submission = CodeSubmission(code=code, language=language, filename=filename)
        except Exception as e:
            await websocket.send_json(
                {"type": "error", "message": f"Invalid submission: {str(e)}"}
            )
            await websocket.close()
            return

        validator = CodeValidator()
        is_valid, error_message = validator.validate(
            submission.code, submission.language
        )

        # Validate
        if not is_valid:
            await websocket.send_json(
                {"type": "error", "message": f"Code validation failed: {error_message}"}
            )
            await websocket.close()
            return

        # Create job
        redis = await get_async_redis()
        job_service = JobService(redis)
        settings = get_settings()

        job_id = await job_service.create_job(
            submission.code, submission.language, submission.filename
        )

        log.info(f"Created job {job_id} for PTY streaming execution")

        # Register connection
        manager.active_connections[job_id] = websocket

        pubsub_service = get_pubsub_service()

        # Define message handler - forwards PTY output to WebSocket
        async def handle_pubsub_message(message: Dict[str, Any]):
            """Forward Pub/Sub messages to WebSocket"""
            await manager.send_message(job_id, message)

        subscription_task = asyncio.create_task(
            pubsub_service.subscribe_to_channels(job_id, handle_pubsub_message)
        )

        await redis.lpush(  # type: ignore[misc]
            "codr:job_queue",
            json.dumps(
                {
                    "job_id": job_id,
                    "code": submission.code,
                    "language": submission.language,
                    "filename": submission.filename,
                    "queued_at": time.time(),
                }
            ),
        )

        log.info(
            f"Job {job_id} queued for worker (queue depth: {await redis.llen('codr:job_queue')})"  # type: ignore[misc]
        )

        # Handle incoming messages - put input directly into queue
        try:
            while True:
                message = await websocket.receive_json()

                if message.get("type") == "input":
                    input_data = message.get("data", "")
                    input_data_kb = len(input_data) * 1024  # input data is in bytes
                    if len(input_data) > settings.max_input_kb:
                        log.warning(
                            f"Input too large for job {job_id}: {len(input_data)} bytes"
                        )
                        await websocket.send_json(
                            {"type": "error", "message": "Input too large (max 10KB)"}
                        )
                        continue
                    await redis.publish(f"job:{job_id}:input", input_data)
                    log.debug(
                        f"Published input to worker for job {job_id}: {input_data[:50]}"
                    )
                else:
                    log.warning(f"Unknown message type: {message.get('type')}")

        except WebSocketDisconnect:
            log.info(f"WebSocket disconnected for job {job_id}")
        except Exception as e:
            log.error(f"Error in WebSocket message loop: {_sanitize_error(e)}")
            await websocket.send_json(
                {"type": "error", "message": f"WebSocket error: {str(e)}"}
            )

    except WebSocketDisconnect:
        log.info("WebSocket disconnected before job creation")
    except Exception as e:
        log.error(f"WebSocket error: {_sanitize_error(e)}")
        try:
            await websocket.send_json(
                {"type": "error", "message": f"Server error: {_sanitize_error(e)}"}
            )
        except Exception:
            pass
    finally:
        # Cleanup
        if job_id:
            manager.disconnect(job_id)
            # Cancel tasks if still running
            if "subscription_task" in locals() and not subscription_task.done():
                subscription_task.cancel()


@router.get("/api/websocket/status")
async def websocket_status(request: Request):
    # Status contains sensitve info, so its protected
    await verify_api_key(request)
    return JSONResponse(
        content={
            "active_connections": len(manager.active_connections),
            "job_ids": list(manager.active_connections.keys()),
        }
    )


def _sanitize_error(error: Exception) -> str:
    if get_settings().env == "development":
        return str(error)
    else:
        return "An Error has occured processing your request"
