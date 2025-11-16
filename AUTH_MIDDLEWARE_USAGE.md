# auth.py Middleware Usage Map

## Quick Answer

**auth.py** currently protects **2 HTTP endpoints** in your application:

1. ✅ `GET /` (root endpoint)
2. ✅ `GET /api/websocket/status` (WebSocket connection status)

---

## All HTTP Endpoints in Your Application

### Protected Endpoints (Require API Key)

| Endpoint | Method | File | Description | Auth Required |
|----------|--------|------|-------------|---------------|
| `/` | GET | `main.py:124` | API information/welcome | ✅ YES |
| `/api/websocket/status` | GET | `websocket.py:214` | WebSocket connection status | ✅ YES |

**These endpoints will return 401/403 if API key is missing or invalid.**

---

### Excluded Endpoints (Public Access)

| Endpoint | Method | File | Description | Auth Required |
|----------|--------|------|-------------|---------------|
| `/health` | GET | `main.py:104` | Health check (Redis status) | ❌ NO (skipped) |
| `/docs` | GET | FastAPI | Interactive API docs | ❌ NO (skipped) |
| `/redoc` | GET | FastAPI | ReDoc API docs | ❌ NO (skipped) |
| `/openapi.json` | GET | FastAPI | OpenAPI schema | ❌ NO (skipped) |

**These endpoints are explicitly excluded from authentication.**

---

### WebSocket Endpoints (NOT protected by auth.py)

| Endpoint | Type | File | Description | Auth Required |
|----------|------|------|-------------|---------------|
| `/ws/execute` | WebSocket | `websocket.py:53` | Code execution | ❌ NO (needs implementation) |

**WebSocket endpoints are NOT protected by `APIKeyMiddleware` because middleware doesn't work with WebSocket connections.**

---

## How auth.py Works

### The Middleware Chain

```python
# main.py:96
app.add_middleware(APIKeyMiddleware)
```

When a request comes in, FastAPI processes it through this flow:

```
HTTP Request
    ↓
┌─────────────────────────────────────┐
│ APIKeyMiddleware (auth.py)          │
├─────────────────────────────────────┤
│ 1. Check if path is excluded        │
│    - /health      → Skip auth ✓     │
│    - /docs        → Skip auth ✓     │
│    - /redoc       → Skip auth ✓     │
│    - /openapi.json → Skip auth ✓    │
│                                     │
│ 2. If not excluded:                 │
│    - Get X-API-Key header           │
│    - Compare with settings.api_key  │
│    - Use secrets.compare_digest()   │
│                                     │
│ 3. Return response:                 │
│    - Valid key   → Continue ✓       │
│    - Invalid key → 403 Forbidden    │
│    - Missing key → 401 Unauthorized │
└─────────────────────────────────────┘
    ↓
Route Handler (your endpoint)
```

---

## Code References

### Middleware Definition (auth.py:55-76)

```python
class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check API key on all requests
    Excludes health check and docs endpoints
    """

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for these paths
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Verify API key
        try:
            await verify_api_key(request)
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

        return await call_next(request)
```

### Middleware Registration (main.py:96)

```python
# Add API key middleware
app.add_middleware(APIKeyMiddleware)
```

This applies the middleware to **ALL HTTP requests** (except WebSocket upgrades).

---

## Protected Endpoints in Detail

### 1. Root Endpoint: `GET /`

**File:** `backend/main.py:124-137`

```python
@app.get("/")
async def root():
    """API information"""
    return {
        "service": "Codr API",
        "version": "2.0.0",
        "description": "Secure code execution platform",
        "endpoints": {
            "websocket": "WS /ws/execute",
            "health": "GET /health",
            "docs": "GET /docs"
        },
        "supported_languages": ["python", "javascript", "c", "cpp", "rust"]
    }
```

**Why protected:** Provides API metadata. While not sensitive, protecting it prevents unauthorized API discovery.

**Testing:**
```bash
# Without API key:
curl http://localhost:8000/
# Response: 401 Unauthorized

# With API key:
curl -H "X-API-Key: your-key" http://localhost:8000/
# Response: API info JSON
```

---

### 2. WebSocket Status: `GET /api/websocket/status`

**File:** `backend/api/websocket.py:214-220`

```python
@router.get("/api/websocket/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return JSONResponse(content={
        "active_connections": len(manager.active_connections),
        "job_ids": list(manager.active_connections.keys())
    })
```

**Why protected:** Shows active WebSocket connections and job IDs. This is **sensitive operational data** that should be protected.

**Testing:**
```bash
# Without API key:
curl http://localhost:8000/api/websocket/status
# Response: 401 Unauthorized

# With API key:
curl -H "X-API-Key: your-key" http://localhost:8000/api/websocket/status
# Response: {"active_connections": 3, "job_ids": ["uuid1", "uuid2", "uuid3"]}
```

---

## Excluded Endpoints in Detail

### 1. Health Check: `GET /health`

**File:** `backend/main.py:104-120`

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        redis = await get_async_redis()
        redis_healthy = await redis.ping()
    except Exception:
        redis_healthy = False

    return JSONResponse(
        status_code=200 if redis_healthy else 503,
        content={
            "status": "healthy" if redis_healthy else "unhealthy",
            "service": "codr-api",
            "redis": "connected" if redis_healthy else "disconnected"
        }
    )
```

**Why excluded:**
- Used by monitoring systems (Kubernetes, Docker, load balancers)
- Needs to be publicly accessible for health probes
- Doesn't expose sensitive data (just service health)

---

### 2. API Documentation: `GET /docs` and `GET /redoc`

**Generated by:** FastAPI (automatic)

**Why excluded:**
- Development convenience
- Common practice to make API docs public (or at least easily accessible)
- Can be removed in production by setting `docs_url=None` and `redoc_url=None` in FastAPI()

**Production consideration:**

```python
# If you want to hide docs in production:
settings = get_settings()

app = FastAPI(
    title="Codr API",
    docs_url="/docs" if settings.env == "development" else None,
    redoc_url="/redoc" if settings.env == "development" else None,
)
```

---

## Security Implications

### What Happens If You Delete auth.py?

```python
# If you delete auth.py and remove this line from main.py:
app.add_middleware(APIKeyMiddleware)  # ← Remove this
```

**Result:**

| Endpoint | Before | After | Impact |
|----------|--------|-------|--------|
| `GET /` | Protected | **Public** | ⚠️ API info exposed |
| `GET /api/websocket/status` | Protected | **Public** | 🔴 **CRITICAL**: Active jobs exposed |
| `GET /health` | Public | Public | ✅ No change |
| `/docs` | Public | Public | ✅ No change |

**Critical issue:** `/api/websocket/status` would expose:
- Number of active connections
- Job IDs currently running
- Potential DoS vector (spam requests to this endpoint)

---

## Current Architecture

```
┌─────────────────────────────────────────────────────┐
│ Incoming HTTP Request                               │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ APIKeyMiddleware (from auth.py)                     │
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ Is path in exclusion list?                  │   │
│ │ [/health, /docs, /redoc, /openapi.json]     │   │
│ └────┬─────────────────────────────────┬──────┘   │
│      │ YES                              │ NO       │
│      ▼                                  ▼          │
│  Skip Auth                      Verify API Key     │
│  (Continue)                     (secrets.compare)  │
│      │                                  │          │
│      │                          Valid? ─┼─ No → 401│
│      │                                  │          │
│      └──────────────┬───────────────────┘          │
│                     │ Yes                          │
└─────────────────────┼──────────────────────────────┘
                      │
                      ▼
           ┌──────────────────────┐
           │ Route Handler        │
           │ (@app.get("/")       │
           │ (websocket_status)   │
           └──────────────────────┘
```

---

## Why This Design?

### Pros ✅

1. **Centralized auth logic** - One place to manage API key validation
2. **Consistent behavior** - All HTTP endpoints follow same auth pattern
3. **Easy to maintain** - Add new endpoints, auto-protected
4. **Secure by default** - New endpoints require API key unless explicitly excluded
5. **Standard pattern** - Middleware-based auth is FastAPI best practice

### Cons ⚠️

1. **All-or-nothing** - Can't easily have per-endpoint auth levels
2. **No role-based access** - Only checks API key presence, not permissions
3. **Single API key** - All valid keys have same access (no user distinction)

---

## Alternative Designs (Not Implemented)

### Option 1: Dependency-Based Auth

```python
from fastapi import Depends
from api.middleware.auth import verify_api_key

@app.get("/api/websocket/status")
async def websocket_status(
    authenticated: bool = Depends(verify_api_key)  # ← Per-endpoint
):
    return {...}
```

**Pros:** Fine-grained control
**Cons:** Must remember to add to each endpoint

---

### Option 2: Route Groups

```python
# Protected routes
protected = APIRouter(dependencies=[Depends(verify_api_key)])

@protected.get("/api/websocket/status")
async def websocket_status():
    ...

app.include_router(protected)
```

**Pros:** Granular route protection
**Cons:** More complex setup

---

## Summary

### What auth.py Currently Protects

✅ **2 HTTP endpoints:**
1. `GET /` (API info)
2. `GET /api/websocket/status` (active connections)

### What It Doesn't Protect

❌ **4 endpoints are excluded:**
1. `GET /health` (intentionally public for monitoring)
2. `GET /docs` (API documentation)
3. `GET /redoc` (alternative API docs)
4. `GET /openapi.json` (OpenAPI schema)

❌ **WebSocket not protected:**
- `WS /ws/execute` (needs separate implementation)

### Why You Need to Keep auth.py

1. **Protects sensitive operational data** (`/api/websocket/status`)
2. **Prevents unauthorized API discovery** (`/`)
3. **Foundation for future HTTP endpoints** (auto-protected when added)
4. **Production-ready security pattern**

---

## Action Items

1. ✅ **KEEP auth.py** - Used by 2 HTTP endpoints
2. ✅ **Implement WebSocket auth separately** - Middleware doesn't work for WS
3. 🔵 **Consider:** Hide docs in production (`docs_url=None`)
4. 🔵 **Future:** Add more granular permissions if needed

**Bottom Line:** auth.py is small but critical. It protects operational endpoints and provides the security foundation for your HTTP API.
