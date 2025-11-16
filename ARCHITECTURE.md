# Codr - Code Sandbox Architecture Documentation

## Executive Summary

Codr is a multilanguage code sandbox executor that safely runs user-submitted code in an isolated environment. The system consists of a FastAPI backend with Firejail sandboxing and a Next.js frontend, communicating via WebSocket for real-time bidirectional I/O.

**Key Metrics:**
- **Total Backend Code:** ~2,921 lines of Python
- **Supported Languages:** Python, JavaScript, C, C++, Rust
- **Architecture Pattern:** Service-oriented with layered security
- **Communication:** WebSocket + Redis Pub/Sub
- **Sandboxing:** Firejail with PTY streaming

---

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Code Editor   │  │  WebSocket   │  │ Terminal Output    │  │
│  │  (Monaco)      │──│  Connection  │──│ (Interactive PTY)  │  │
│  └────────────────┘  └──────────────┘  └────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────┘
                             │ WS Connection
                             │
┌────────────────────────────┴─────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Middleware   │  │  WebSocket   │  │  Service Layer     │    │
│  │ - Auth       │──│  Handler     │──│  - Execution       │    │
│  │ - Rate Limit │  │              │  │  - Job Manager     │    │
│  │ - CORS       │  │              │  │  - PubSub          │    │
│  └──────────────┘  └──────────────┘  └─────────┬──────────┘    │
│                                                  │                │
│  ┌──────────────────────────────────────────────┼──────────┐    │
│  │             Security Layer                   │          │    │
│  │  ┌─────────────────┐  ┌────────────────────┐ │          │    │
│  │  │ AST Validators  │  │ Code Validator     │ │          │    │
│  │  │ - Python        │  │ - Pattern Matching │ │          │    │
│  │  │ - JavaScript    │  │ - Blocklist Check  │ │          │    │
│  │  │ - C/C++         │  │                    │ │          │    │
│  │  │ - Rust          │  │                    │ │          │    │
│  │  └─────────────────┘  └────────────────────┘ │          │    │
│  └──────────────────────────────────────────────┼──────────┘    │
│                                                  │                │
│  ┌──────────────────────────────────────────────┼──────────┐    │
│  │             Executor Layer                   │          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┴──┐       │    │
│  │  │  Python  │  │JavaScript│  │  Compiled Base  │       │    │
│  │  │ Executor │  │ Executor │  │  - C Executor   │       │    │
│  │  └──────────┘  └──────────┘  │  - C++ Executor │       │    │
│  │                               │  - Rust Executor│       │    │
│  │                               └─────────────────┘       │    │
│  └────────────────────────────────────┬──────────────────────    │
└────────────────────────────────────────┼──────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
         ┌──────────▼────────┐  ┌────────▼────────┐  ┌───────▼──────┐
         │  Firejail Sandbox │  │  PTY Streaming  │  │    Redis     │
         │  - Network: None  │  │  - Bidirectional│  │  - Job Store │
         │  - Memory: 300MB  │  │  - Real-time    │  │  - Pub/Sub   │
         │  - Time: 7s       │  │  I/O            │  │              │
         └───────────────────┘  └─────────────────┘  └──────────────┘
```

---

## Component Breakdown

### 1. Frontend Layer (Next.js)

**Location:** `/nextjs/`

#### Core Components
- **CodeEditor** (`components/CodeEditor.tsx`): Monaco-based code editor
- **InteractiveTerminalOutput** (`components/InteractiveTerminalOutput.tsx`): PTY terminal display
- **IDE** (`components/ide.tsx`): Main integration component

#### Hooks
- **useWebSocketExecution** (`hooks/useWebSocketExecution.ts`): WebSocket management and execution logic
- **useFileOperations**: File management (save/load)
- **useEditorSettings**: Editor configuration

#### Configuration
- **languageConfig.ts**: Language-specific settings (extensions, Monaco modes)
- **editorConfig.ts**: Monaco editor configuration

---

### 2. Backend Layer (FastAPI)

**Location:** `/backend/`

#### Entry Point
- **main.py**: FastAPI application setup, middleware configuration, lifespan management

#### API Layer (`/api/`)

**WebSocket Handler** (`websocket.py`):
- Connection manager for active WebSocket sessions
- Message protocol handler (execute, input, output, complete, error)
- Bridges WebSocket ↔ Redis Pub/Sub

**Middleware** (`/middleware/`):
- `auth.py`: API key authentication with constant-time comparison
- `rate_limiter.py`: SlowAPI-based rate limiting (10/min submit, 30/min stream)

**Models** (`/models/`):
- `schema.py`: Pydantic models (CodeSubmission, JobResponse, JobResult)
- `allowlist.py`: Security blocklists for all languages

**Services** (`/services/`):
- `execution_service.py`: Manages code execution, bridges executors with Pub/Sub
- `job_service.py`: Job lifecycle management (CRUD operations in Redis)
- `pubsub_service.py`: Redis Pub/Sub messaging for real-time communication

**Security** (`/security/`):
- `validator.py`: Main validation dispatcher
- `ast_validator.py`: Tree-sitter parser wrapper
- `python_ast_validator.py`: Python AST analysis
- `javascript_ast_validator.py`: JavaScript AST analysis
- `c_cpp_ast_validator.py`: C/C++ AST analysis
- `rust_ast_validator.py`: Rust AST analysis

**Connection Management** (`/connect/`):
- `redis_manager.py`: Singleton async Redis connection manager

---

### 3. Executor Layer (`/executors/`)

**Base Classes:**
- **BaseExecutor** (`base.py`): Abstract base with PTY streaming logic
- **CompiledExecutor** (`compiled_base.py`): Compilation logic for compiled languages

**Language Executors:**
- **PythonExecutor** (`python.py`): Runs Python via `python3`
- **JavaScriptExecutor** (`javascript.py`): Runs JavaScript via `node`
- **CExecutor** (`c.py`): Compiles with `gcc` (C11 standard)
- **CppExecutor** (`cpp.py`): Compiles with `g++` (C++17 standard)
- **RustExecutor** (`rust.py`): Compiles with `rustc`

**Executor Registry** (`__init__.py`):
- Factory pattern for executor instantiation
- Language support validation

---

### 4. Configuration Layer (`/config/`)

**settings.py**: Pydantic-based configuration management
- Server config (host, port, environment)
- Execution limits (timeout, memory, file size)
- Redis connection settings
- Rate limiting configuration

---

### 5. Infrastructure Layer

**Redis:**
- **Job Storage**: Redis Hash for job metadata
- **Pub/Sub Channels**:
  - `job:{job_id}:output` - Streaming output
  - `job:{job_id}:complete` - Completion events

**Firejail Sandbox:**
- Network isolation (`--net=none`)
- Memory limit (`--rlimit-as=300MB`)
- CPU time limit (`--rlimit-cpu=7s`)
- File size limit (`--rlimit-fsize=1MB`)
- No root access (`--noroot`)
- No D-Bus (`--nodbus`)
- Private filesystem

---

## Data Flow Diagrams

### Code Execution Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │ 1. Submit code
     ▼
┌─────────────────┐
│  WebSocket      │
│  Connection     │
└────┬────────────┘
     │ 2. {type: "execute", code, language}
     ▼
┌─────────────────┐
│  Validation     │──── AST Analysis
│  Layer          │──── Blocklist Check
└────┬────────────┘
     │ 3. Valid
     ▼
┌─────────────────┐
│  Job Service    │──── Create UUID
│                 │──── Store in Redis
└────┬────────────┘
     │ 4. job_id
     ▼
┌─────────────────┐
│  Execution      │──── Get Executor
│  Service        │──── Setup PTY
└────┬────────────┘
     │ 5. Start execution
     ▼
┌─────────────────┐
│  Executor       │──── Write code to tmpfile
│  (Language)     │──── Compile (if needed)
└────┬────────────┘
     │ 6. Run in Firejail
     ▼
┌─────────────────┐
│  PTY Process    │──── Execute code
│                 │──── Capture I/O
└────┬────────────┘
     │ 7. Stream output
     ▼
┌─────────────────┐
│  Redis Pub/Sub  │──── Publish to channel
│                 │──── job:{job_id}:output
└────┬────────────┘
     │ 8. Forward message
     ▼
┌─────────────────┐
│  WebSocket      │──── {type: "output", data}
│  Handler        │
└────┬────────────┘
     │ 9. Display output
     ▼
┌─────────────────┐
│  Frontend       │──── Update terminal
│  Terminal       │
└─────────────────┘
```

### Interactive Input Flow

```
┌─────────┐
│  Code   │──── input("Enter name: ")
└────┬────┘
     │ PTY waiting for input
     ▼
┌─────────────────┐
│  Frontend       │──── Show input field
│  (PTY Terminal) │
└────┬────────────┘
     │ User types "Alice"
     ▼
┌─────────────────┐
│  WebSocket      │──── {type: "input", data: "Alice\n"}
│                 │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Input Queue    │──── asyncio.Queue → queue.Queue
│  Bridge         │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  PTY Master     │──── os.write(master_fd, "Alice\n")
│                 │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Code Process   │──── Receives input
│                 │──── Continues execution
└─────────────────┘
```

---

## Security Architecture

### Multi-Layer Security Model

**Layer 1: Input Validation**
- Pydantic schema validation (code size ≤10KB, filename format)
- Path traversal prevention

**Layer 2: AST Analysis**
- Tree-sitter parsing for JavaScript, C/C++, Rust
- Python's built-in AST module
- Blocklist enforcement:
  - Dangerous functions (eval, exec, system, socket, etc.)
  - Dangerous modules (os, subprocess, fs, net, etc.)
  - Dangerous patterns (process.binding, globalThis, etc.)

**Layer 3: Sandbox Isolation**
- Firejail containerization
- Network disabled
- Filesystem isolation
- Resource limits (CPU, memory, disk)

**Layer 4: Authentication & Rate Limiting**
- API key authentication (constant-time comparison)
- Rate limiting (SlowAPI)
- CORS configuration

---

## Technology Stack

### Backend
- **Framework:** FastAPI 0.104+
- **Language:** Python 3.11+
- **Async Runtime:** asyncio
- **Database:** Redis (async)
- **Validation:** Pydantic, tree-sitter
- **Sandboxing:** Firejail
- **Server:** Uvicorn

### Frontend
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Editor:** Monaco Editor
- **Styling:** Tailwind CSS
- **HTTP Client:** Native WebSocket API

### Infrastructure
- **Cache/Queue:** Redis
- **Deployment:** Fly.io (configured)
- **Container:** Docker

---

## File Structure

```
codr-beta/
├── backend/
│   ├── api/
│   │   ├── connect/          # Redis connection management
│   │   ├── middleware/       # Auth, rate limiting
│   │   ├── models/           # Pydantic schemas, security blocklists
│   │   ├── security/         # AST validators
│   │   ├── services/         # Business logic (execution, jobs, pubsub)
│   │   └── websocket.py      # WebSocket endpoint
│   ├── config/               # Settings management
│   ├── executors/            # Language-specific execution
│   ├── logger/               # Logging configuration
│   ├── main.py              # FastAPI app entry point
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Backend container
├── nextjs/
│   ├── app/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── config/          # Frontend configuration
│   │   └── lib/             # Utility functions
│   ├── package.json         # Node dependencies
│   └── tsconfig.json        # TypeScript config
├── test_interactive/        # Interactive input test files
├── ExecutionFlow.md         # Existing flow documentation
├── PTY.md                   # PTY implementation notes
└── DEPLOY_TO_FLYIO.md       # Deployment guide
```

---

## Key Design Decisions

### 1. PTY Streaming vs. Batch Execution
**Decision:** Use PTY (pseudo-terminal) for real-time streaming
**Rationale:**
- Industry standard (same as xterm.js + node-pty)
- Natural handling of interactive input
- Real-time output without buffering
- Simpler than prompt detection heuristics

### 2. WebSocket vs. HTTP Polling
**Decision:** WebSocket for execution, HTTP for metadata
**Rationale:**
- Bidirectional real-time communication
- Lower latency for streaming output
- Efficient for interactive input
- Better user experience

### 3. Redis Pub/Sub vs. Direct Connection
**Decision:** Redis Pub/Sub for output streaming
**Rationale:**
- Horizontal scalability (WebSocket server ≠ Executor server)
- Decoupled architecture
- Message broadcasting support
- Fault tolerance

### 4. AST Validation vs. Regex
**Decision:** AST-based validation (strict mode, no fallback)
**Rationale:**
- More accurate than regex
- Harder to bypass with obfuscation
- Language-aware analysis
- Better error messages

### 5. Firejail vs. Docker
**Decision:** Firejail for sandboxing
**Rationale:**
- Lightweight (no container overhead)
- Fast startup time
- Fine-grained resource control
- Sufficient isolation for code execution

---

## Configuration

### Environment Variables

**Backend (.env):**
```bash
# Server
ENV=production
API_KEY=your-secret-key
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=*

# Execution
EXECUTION_TIMEOUT=7
MAX_MEMORY_MB=300
MAX_FILE_SIZE_MB=1
COMPILATION_TIMEOUT=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_TTL=3600

# Rate Limiting
RATE_LIMIT_SUBMIT=10/minute
RATE_LIMIT_STREAM=30/minute
```

**Frontend (.env):**
```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## Performance Characteristics

### Execution Times (Approximate)
- **Python:** ~50-100ms startup + execution time
- **JavaScript:** ~100-150ms startup + execution time
- **C:** ~500-1000ms compilation + execution time
- **C++:** ~1000-2000ms compilation + execution time
- **Rust:** ~2000-5000ms compilation + execution time

### Resource Limits
- **Memory:** 300MB per execution
- **CPU Time:** 7 seconds
- **Output Size:** 1MB
- **Code Size:** 10KB

### Scalability
- **Concurrent Jobs:** Limited by Redis + Server resources
- **Horizontal Scaling:** Supported via Redis Pub/Sub
- **Connection Limits:** Configurable via rate limiting

---

## Dependencies

### Backend (requirements.txt)
```
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
redis[hiredis]>=5.0.1
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
slowapi>=0.1.9
tree-sitter>=0.20.4
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "@monaco-editor/react": "^4.6.0",
    "tailwindcss": "^3.3.0"
  }
}
```

---

## Deployment Architecture

### Production Setup (Fly.io)
```
┌─────────────────────────────────────────────┐
│           Fly.io Edge Network               │
│  ┌─────────────┐         ┌────────────┐    │
│  │   Next.js   │         │  Backend   │    │
│  │   Frontend  │────────▶│   (API)    │    │
│  │             │  WS/HTTP │            │    │
│  └─────────────┘         └──────┬─────┘    │
│                                  │          │
│                          ┌───────▼──────┐   │
│                          │  Upstash     │   │
│                          │  Redis       │   │
│                          └──────────────┘   │
└─────────────────────────────────────────────┘
```

---

## Extension Points

### Adding a New Language

1. Create executor in `backend/executors/`:
   ```python
   from .base import BaseExecutor

   class NewLanguageExecutor(BaseExecutor):
       def _build_command(self, filepath: str, workdir: str) -> List[str]:
           return ['interpreter', filepath]
   ```

2. Add to executor registry in `executors/__init__.py`

3. Create AST validator in `api/security/` (if needed)

4. Add blocklist patterns to `api/models/allowlist.py`

5. Update language config in frontend `config/languageConfig.ts`

### Adding New Security Rules

1. Add patterns to `backend/api/models/allowlist.py`
2. Update corresponding AST validator
3. Test with bypass attempts

---

## Monitoring & Observability

### Health Check
- **Endpoint:** `GET /health`
- **Checks:** Redis connectivity

### Logging
- Structured logging via `logger/logger.py`
- Log levels: DEBUG, INFO, WARNING, ERROR
- Output: stdout (container-friendly)

### Metrics (Not Implemented)
- Execution count
- Average execution time
- Error rate
- Queue depth

---

## Known Limitations

1. **No execution history** - Jobs expire after TTL (1 hour)
2. **Single Redis instance** - No HA/failover configured
3. **No authentication for WebSocket** - Relies on API key for REST
4. **Fixed resource limits** - Not configurable per user/language
5. **No code sharing** - No URL-based code sharing feature

---

## Production Readiness Assessment

### ✅ Production Ready
- Security (multi-layer defense)
- Error handling
- Configuration management
- Sandboxing
- Rate limiting
- CORS configuration

### ⚠️ Needs Consideration
- Monitoring/alerting (no metrics collection)
- Logging aggregation (using stdout only)
- Redis HA setup
- WebSocket authentication
- Graceful degradation
- Load testing results

### 🔄 Future Enhancements
- User authentication
- Execution history
- Code sharing/permalinks
- Multi-language detection
- Syntax highlighting improvements
- Mobile responsiveness
