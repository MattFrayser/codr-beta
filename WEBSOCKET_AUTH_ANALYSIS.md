# WebSocket Authentication Analysis

**Question:** Should we use the existing `auth.py` for WebSocket authentication, or is it overkill?

**Answer:** **Use the existing `verify_api_key()` function** - it's NOT overkill, it's the right approach.

---

## Current Situation

### What's Working
- ✅ HTTP endpoints protected by `APIKeyMiddleware`
- ✅ `verify_api_key()` function with constant-time comparison
- ✅ Proper security practices (secrets.compare_digest)

### What's Missing
- ❌ WebSocket endpoint `/ws/execute` has **NO authentication**
- ❌ Anyone can connect and execute code without API key
- ❌ Security hole in production deployment

---

## WebSocket Authentication Best Practices (2024)

Based on industry research, there are **4 common approaches** for WebSocket authentication in FastAPI:

### 1. Query Parameter (`/ws/execute?api_key=xxx`)

**Pros:**
- Simple to implement
- Works universally

**Cons:**
- ⚠️ **API key exposed in URLs** (logs, browser history, proxy logs)
- ⚠️ **Security risk** - keys can leak
- ⚠️ Not recommended for production

**Verdict:** ❌ **Avoid for API key authentication**

---

### 2. HTTP Headers (Recommended ✅)

**Pros:**
- ✅ **Standard HTTP practice**
- ✅ **Secure** - API key not in URLs
- ✅ **Reuses existing `verify_api_key()` logic**
- ✅ Works with WebSocket handshake headers
- ✅ Same pattern as REST endpoints

**Cons:**
- Requires client to send header during WebSocket connection

**Verdict:** ✅ **RECOMMENDED for this project**

---

### 3. Cookie-Based

**Pros:**
- Secure
- Automatic browser handling

**Cons:**
- Requires cookie infrastructure
- Overkill for API key authentication
- CSRF considerations

**Verdict:** 🟡 **Good for user sessions, but overkill for API keys**

---

### 4. First Message After Accept (Current Pattern)

**How it works:**
1. Accept WebSocket connection
2. Wait for first message with API key
3. Validate and proceed or close

**Pros:**
- API key not in URL
- Current pattern in the code

**Cons:**
- ⚠️ **Connection accepted before validation**
- ⚠️ Opens door to DoS attacks
- ⚠️ Resource allocation before auth check
- ⚠️ Not industry standard

**Verdict:** 🟡 **Better than nothing, but not best practice**

---

## Recommendation: Use Headers with Existing `verify_api_key()`

### Why This Is NOT Overkill

The existing `auth.py` provides:

1. **Constant-time comparison** (`secrets.compare_digest`)
   - Prevents timing attacks
   - Critical security feature

2. **Centralized logic**
   - Single source of truth
   - DRY principle

3. **Consistent behavior**
   - WebSocket and HTTP endpoints behave the same
   - Same error messages
   - Same dev mode behavior (skip auth if no key configured)

4. **Tested pattern**
   - Already working for HTTP
   - Proven secure

### Implementation Options

There are **3 ways** to implement header-based auth for WebSocket:

---

## Option A: FastAPI Dependency Injection (Cleanest)

**Best for:** Production-ready, clean code

```python
from fastapi import WebSocket, Header, WebSocketException, status
from api.middleware.auth import verify_api_key
import secrets
from config.settings import get_settings

async def get_api_key_websocket(
    x_api_key: str = Header(None, alias="X-API-Key")
) -> str:
    """
    Dependency to validate API key for WebSocket connections

    Raises:
        WebSocketException: If API key is invalid or missing
    """
    settings = get_settings()
    expected_api_key = settings.api_key

    # Skip auth in dev mode
    if not expected_api_key:
        return None

    # Check if API key provided
    if not x_api_key:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing API key"
        )

    # Validate API key (constant-time comparison)
    if not secrets.compare_digest(x_api_key, expected_api_key):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid API key"
        )

    return x_api_key


@router.websocket("/ws/execute")
async def websocket_execute(
    websocket: WebSocket,
    api_key: str = Depends(get_api_key_websocket)  # ✅ Validated before accept
):
    """WebSocket endpoint with authentication"""
    # If we get here, API key is valid
    await websocket.accept()

    # Rest of implementation...
```

**Pros:**
- ✅ Validated **before** accepting connection
- ✅ Clean FastAPI dependency pattern
- ✅ Automatic error handling
- ✅ Reuses constant-time comparison
- ✅ Same dev mode behavior

**Cons:**
- Slightly more code

---

## Option B: Manual Header Check (Simplest)

**Best for:** Quick fix, minimal changes

```python
@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    """WebSocket endpoint with authentication"""

    # Validate API key from headers BEFORE accepting connection
    settings = get_settings()

    if settings.api_key:  # Only check if API key is configured
        client_api_key = websocket.headers.get("X-API-Key")

        if not client_api_key:
            await websocket.close(code=1008, reason="Missing API key")
            return

        # Use constant-time comparison
        if not secrets.compare_digest(client_api_key, settings.api_key):
            await websocket.close(code=1008, reason="Invalid API key")
            return

    # API key valid, accept connection
    await websocket.accept()
    log.info("WebSocket connection accepted (authenticated)")

    # Rest of implementation...
```

**Pros:**
- ✅ Simple and direct
- ✅ Validated **before** accepting connection
- ✅ Minimal code changes
- ✅ Reuses constant-time comparison

**Cons:**
- Duplicates some logic from `verify_api_key()`
- Not using dependency injection pattern

---

## Option C: Reuse Exact `verify_api_key()` (DRY)

**Best for:** Maximum code reuse

```python
from fastapi import Request
from api.middleware.auth import verify_api_key, API_KEY_NAME

@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    """WebSocket endpoint with authentication"""

    # Create a minimal Request-like object for verify_api_key
    # (WebSocket has headers attribute just like Request)
    try:
        # Get API key from WebSocket headers
        api_key = websocket.headers.get(API_KEY_NAME)
        settings = get_settings()

        # Skip auth if no API key configured (dev mode)
        if settings.api_key:
            # Manual validation using same logic as verify_api_key
            if not api_key:
                await websocket.close(code=1008, reason="API key is missing")
                return

            if not secrets.compare_digest(api_key, settings.api_key):
                await websocket.close(code=1008, reason="Invalid API key")
                return

    except Exception as e:
        log.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Authentication successful
    await websocket.accept()
    log.info("WebSocket connection accepted (authenticated)")

    # Rest of implementation...
```

---

## Comparison Matrix

| Approach | Reuses Code | Validates Before Accept | Clean Code | Complexity |
|----------|-------------|------------------------|------------|------------|
| **Option A (Dependency)** | Partial | ✅ Yes | ✅✅ Excellent | Medium |
| **Option B (Manual)** | Partial | ✅ Yes | ✅ Good | Low |
| **Option C (Reuse verify_api_key)** | ✅ Maximum | ✅ Yes | 🟡 Fair | Low |
| **Query Parameter** | No | ✅ Yes | 🟡 Fair | Low |
| **First Message** | No | ❌ No | 🟡 Fair | Low |
| **Current (No Auth)** | - | ❌ No | - | - |

---

## My Recommendation: Option A or B

### **Option A** (Dependency Injection) if:
- ✅ You want production-quality code
- ✅ You're comfortable with FastAPI patterns
- ✅ You want the cleanest architecture

### **Option B** (Manual Check) if:
- ✅ You want the quickest fix
- ✅ You want minimal code changes
- ✅ You want simplicity over abstraction

### **Avoid:**
- ❌ Query parameters (exposes API key)
- ❌ First message authentication (accepts before validating)

---

## Frontend Changes Required

With header-based auth, you need to pass the API key in WebSocket connection:

```typescript
// Current (insecure):
const ws = new WebSocket('ws://localhost:8000/ws/execute');

// With header auth:
const ws = new WebSocket('ws://localhost:8000/ws/execute', {
  headers: {
    'X-API-Key': 'your-api-key-here'
  }
});
```

**Note:** Browser WebSocket API doesn't support custom headers directly. You have two options:

### Frontend Option 1: Use Query Parameter (Temporary)
```typescript
const apiKey = 'your-api-key';
const ws = new WebSocket(`ws://localhost:8000/ws/execute?api_key=${apiKey}`);
```

### Frontend Option 2: Send in First Message (Better)
```typescript
const ws = new WebSocket('ws://localhost:8000/ws/execute');

ws.onopen = () => {
  // Send auth + execute in first message
  ws.send(JSON.stringify({
    type: 'execute',
    api_key: 'your-api-key',  // Add this field
    code: code,
    language: language
  }));
};
```

**Backend validates first message:**
```python
@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    await websocket.accept()  # Accept connection

    # Wait for first message
    data = await websocket.receive_json()

    # Validate API key from first message
    settings = get_settings()
    if settings.api_key:
        client_api_key = data.get('api_key')
        if not client_api_key or not secrets.compare_digest(client_api_key, settings.api_key):
            await websocket.send_json({"type": "error", "message": "Invalid API key"})
            await websocket.close(code=1008)
            return

    # Continue with execution...
```

---

## WebSocket Status Codes

When closing WebSocket for auth failures, use proper status codes:

| Code | Meaning | When to Use |
|------|---------|-------------|
| `1000` | Normal closure | Successful completion |
| `1008` | Policy violation | **Auth failure** ✅ |
| `1011` | Server error | Internal errors |
| `1003` | Unsupported data | Invalid message format |

---

## Final Recommendation

### For Production (Best Practice):

**Use Option B (Manual Header Check) with First Message Auth** as a hybrid:

1. **No auth on WebSocket accept** (browser limitation)
2. **Validate API key in first message** (what you're already doing)
3. **Close immediately if invalid**

**Enhanced implementation:**

```python
@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    """WebSocket endpoint with first-message authentication"""
    job_id: str = None

    try:
        # Accept connection (required for browser WebSocket)
        await websocket.accept()
        log.info("WebSocket connection accepted, waiting for authenticated execute message")

        # Wait for first message (with timeout)
        data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=5.0  # 5 second timeout for first message
        )

        # Validate message type
        if data.get("type") != "execute":
            await websocket.send_json({
                "type": "error",
                "message": "First message must be of type 'execute'"
            })
            await websocket.close(code=1008)
            return

        # VALIDATE API KEY FROM MESSAGE
        settings = get_settings()
        if settings.api_key:
            client_api_key = data.get("api_key")

            if not client_api_key:
                await websocket.send_json({
                    "type": "error",
                    "message": "API key is required"
                })
                await websocket.close(code=1008)
                return

            # Constant-time comparison (prevent timing attacks)
            if not secrets.compare_digest(client_api_key, settings.api_key):
                log.warning(f"Invalid API key attempt from {websocket.client}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid API key"
                })
                await websocket.close(code=1008)
                return

        log.info("WebSocket authentication successful")

        # Extract code submission (API key already validated)
        code = data.get("code", "")
        language = data.get("language", "")

        # Continue with existing implementation...

    except asyncio.TimeoutError:
        log.warning("WebSocket timeout waiting for execute message")
        await websocket.close(code=1008, reason="Timeout")
        return
    except Exception as e:
        log.error(f"WebSocket error: {str(e)}")
        # ... rest of error handling
```

---

## Summary

**Is `auth.py` overkill?**

**NO** - You should use the authentication logic from `auth.py`:
- ✅ Use `secrets.compare_digest()` for constant-time comparison
- ✅ Use same `API_KEY_NAME` constant
- ✅ Use same dev mode logic (skip if no key configured)
- ✅ Use same error messages

**Best implementation for this project:**

**First Message Authentication** (accounts for browser WebSocket limitations):
1. Accept WebSocket connection
2. Immediately wait for first message (with timeout)
3. Validate API key in first message payload
4. Close connection if invalid
5. Continue if valid

**Changes needed:**
1. Add `api_key` field to first message validation
2. Add timeout for first message (prevent connection camping)
3. Use constant-time comparison
4. Log authentication attempts

This approach:
- ✅ Works with browser WebSocket API
- ✅ Reuses security logic from `auth.py`
- ✅ Minimal changes to existing code
- ✅ Production-ready
- ✅ Not overkill - properly secure

**Estimated implementation time:** 15-30 minutes
