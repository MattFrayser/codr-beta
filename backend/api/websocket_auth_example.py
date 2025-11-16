"""
Example: WebSocket Authentication Implementation

This file demonstrates the RECOMMENDED approach for adding API key
authentication to the WebSocket endpoint.

This is a complete working example showing the first-message authentication
pattern, which works with browser WebSocket limitations.
"""

import asyncio
import secrets
from fastapi import WebSocket, WebSocketDisconnect
from config.settings import get_settings
from logger.logger import log

# Import the API key header name from existing auth module
from api.middleware.auth import API_KEY_NAME


async def websocket_execute_with_auth(websocket: WebSocket):
    """
    WebSocket endpoint with first-message authentication

    This implementation:
    1. Accepts connection (required for browser WebSocket)
    2. Waits for first message with timeout
    3. Validates API key in message payload
    4. Closes connection immediately if invalid
    5. Continues with execution if valid

    Protocol:
    - Client must send API key in first 'execute' message
    - Server validates before processing
    - Connection closed on auth failure with clear error
    """
    job_id: str = None

    try:
        # Step 1: Accept connection
        # (Required because browser WebSocket API doesn't support custom headers)
        await websocket.accept()
        log.info("WebSocket connection accepted, waiting for authenticated execute message")

        # Step 2: Wait for first message with timeout
        # This prevents attackers from holding connections open
        try:
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=5.0  # 5 second timeout for first message
            )
        except asyncio.TimeoutError:
            log.warning("WebSocket timeout waiting for execute message")
            await websocket.close(code=1008, reason="Authentication timeout")
            return

        # Step 3: Validate message structure
        if data.get("type") != "execute":
            await websocket.send_json({
                "type": "error",
                "message": "First message must be of type 'execute'"
            })
            await websocket.close(code=1008)
            return

        # Step 4: VALIDATE API KEY
        settings = get_settings()

        # Only require API key if one is configured (allows dev mode)
        if settings.api_key:
            client_api_key = data.get("api_key")

            # Check if API key was provided
            if not client_api_key:
                log.warning(f"Missing API key from {websocket.client}")
                await websocket.send_json({
                    "type": "error",
                    "message": "API key is required"
                })
                await websocket.close(code=1008)
                return

            # SECURITY: Use constant-time comparison to prevent timing attacks
            # This is the SAME security measure used in auth.py
            if not secrets.compare_digest(client_api_key, settings.api_key):
                log.warning(f"Invalid API key attempt from {websocket.client}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid API key"
                })
                await websocket.close(code=1008)
                return

            log.info(f"WebSocket authentication successful from {websocket.client}")

        # Step 5: Authentication successful - proceed with execution
        code = data.get("code", "")
        language = data.get("language", "")

        # Validate submission data
        if not code or not language:
            await websocket.send_json({
                "type": "error",
                "message": "Code and language are required"
            })
            await websocket.close()
            return

        # Continue with existing implementation...
        # (All your existing code execution logic goes here)

        log.info("Proceeding with code execution")
        # ... rest of websocket_execute implementation ...

    except WebSocketDisconnect:
        log.info("WebSocket disconnected before job creation")
    except Exception as e:
        log.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
        except:
            pass


# ============================================================================
# ALTERNATIVE: Dependency Injection Pattern (More FastAPI-idiomatic)
# ============================================================================

from fastapi import Depends, status
from fastapi.exceptions import WebSocketException


async def verify_websocket_api_key(
    websocket: WebSocket,
    first_message: dict = None
) -> bool:
    """
    Dependency function to validate API key from WebSocket first message

    This can be used with FastAPI's Depends() pattern for cleaner code.
    However, it requires accepting the connection first to read the message.

    Args:
        websocket: WebSocket connection
        first_message: First message from client (must contain api_key)

    Returns:
        True if authenticated

    Raises:
        WebSocketException: If authentication fails
    """
    settings = get_settings()

    # Skip auth in dev mode
    if not settings.api_key:
        return True

    # Get API key from first message
    if not first_message:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing authentication message"
        )

    client_api_key = first_message.get("api_key")

    if not client_api_key:
        log.warning("Missing API key in WebSocket message")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="API key is required"
        )

    # Constant-time comparison (prevents timing attacks)
    if not secrets.compare_digest(client_api_key, settings.api_key):
        log.warning(f"Invalid API key attempt")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid API key"
        )

    log.info("WebSocket authentication successful")
    return True


# ============================================================================
# FRONTEND CHANGES REQUIRED
# ============================================================================

"""
JavaScript/TypeScript frontend changes needed:

// OLD (no authentication):
const ws = new WebSocket('ws://localhost:8000/ws/execute');
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'execute',
    code: code,
    language: language
  }));
};

// NEW (with API key authentication):
const ws = new WebSocket('ws://localhost:8000/ws/execute');
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'execute',
    api_key: 'your-api-key-here',  // ← ADD THIS
    code: code,
    language: language
  }));
};

// Store API key securely (environment variable or config):
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-key';

// In production, get from secure storage:
const ws = new WebSocket(wsUrl);
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'execute',
    api_key: API_KEY,
    code: code,
    language: language
  }));
};

// Handle auth errors:
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'error') {
    if (message.message.includes('API key')) {
      // Handle authentication error
      console.error('Authentication failed:', message.message);
      // Show user-friendly message
      addOutputLine('system', 'Authentication failed. Please check your API key.');
    }
  }
};
"""


# ============================================================================
# TESTING THE AUTHENTICATION
# ============================================================================

"""
Manual testing steps:

1. Test with valid API key:
   wscat -c "ws://localhost:8000/ws/execute"
   > {"type": "execute", "api_key": "your-key", "code": "print('test')", "language": "python"}

   Expected: Connection accepted, code executes

2. Test with missing API key:
   wscat -c "ws://localhost:8000/ws/execute"
   > {"type": "execute", "code": "print('test')", "language": "python"}

   Expected: Error message, connection closed with code 1008

3. Test with invalid API key:
   wscat -c "ws://localhost:8000/ws/execute"
   > {"type": "execute", "api_key": "wrong-key", "code": "print('test')", "language": "python"}

   Expected: Error message, connection closed with code 1008

4. Test timeout:
   wscat -c "ws://localhost:8000/ws/execute"
   (wait 6 seconds without sending message)

   Expected: Connection closed due to timeout

5. Test dev mode (no API key configured):
   Unset API_KEY environment variable
   wscat -c "ws://localhost:8000/ws/execute"
   > {"type": "execute", "code": "print('test')", "language": "python"}

   Expected: Connection accepted (auth skipped in dev mode)
"""
