# Startup and Execution Flow Documentation

This document provides a detailed walkthrough of function calls during application startup and when executing code in each supported language.

---

## Table of Contents
1. [Backend Startup Flow](#backend-startup-flow)
2. [Frontend Startup Flow](#frontend-startup-flow)
3. [Code Execution Flow by Language](#code-execution-flow-by-language)
4. [Function Call Sequences](#function-call-sequences)

---

## Backend Startup Flow

### 1. Application Entry Point

**File:** `backend/main.py`

```
main.py execution
│
├─► load_dotenv()                          # Load .env file
│
├─► sys.path.insert(0, backend_dir)       # Add backend to Python path
│
├─► get_settings()                         # Initialize configuration
│   └─► AppSettings.__init__()
│       └─► BaseSettings.__init__()       # Pydantic settings from env vars
│
├─► FastAPI.__init__()                     # Create FastAPI app
│   ├─► title="Codr API"
│   ├─► version="2.0.0"
│   └─► lifespan=lifespan                 # Register lifecycle manager
│
├─► app.add_middleware(CORSMiddleware)     # Configure CORS
│   └─► get_settings().get_cors_origins_list()
│
├─► app.add_middleware(APIKeyMiddleware)   # Add API key auth
│
├─► app.state.limiter = limiter           # Add rate limiter
│
├─► app.include_router(websocket_router)   # Register WebSocket routes
│
└─► uvicorn.run()                         # Start server (if __main__)
    └─► Triggers lifespan() context manager
```

### 2. Lifespan Events

**Function:** `lifespan(app: FastAPI)`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    ├─► get_async_redis()                          # Initialize Redis connection
    │   └─► AsyncRedisManager.get_connection()
    │       ├─► get_settings()
    │       ├─► aioredis.from_url(redis_url)
    │       │   ├─► socket_connect_timeout=5
    │       │   ├─► socket_timeout=5
    │       │   └─► health_check_interval=30
    │       ├─► redis.ping()                       # Test connection
    │       └─► log.info("Redis connection established")
    │
    ├─► JobService.__init__(redis_client)          # Initialize job service
    │   └─► app.state.job_service = JobService
    │
    ├─► get_settings().api_key                     # Check API key
    │   └─► log.warning() if not set
    │
    └─► yield                                      # Application runs...

        # ===== SHUTDOWN =====
        ├─► log.info("Shutting down...")
        └─► AsyncRedisManager.close_connection()
            ├─► redis.close()
            └─► log.info("Redis connection closed")
```

### 3. Middleware Stack (Request Processing Order)

For each incoming request:

```
HTTP Request
│
├─► CORSMiddleware.dispatch()                  # CORS headers
│   ├─► Check origin
│   └─► Add headers (Access-Control-*)
│
├─► APIKeyMiddleware.dispatch()                # Authentication
│   ├─► Skip if path in ["/health", "/docs", "/redoc", "/openapi.json"]
│   ├─► verify_api_key(request)
│   │   ├─► get_settings().api_key
│   │   ├─► request.headers.get("X-API-Key")
│   │   ├─► secrets.compare_digest()           # Constant-time comparison
│   │   └─► raise HTTPException if invalid
│   └─► call_next(request)
│
├─► SlowAPI Rate Limiter (if endpoint decorated)
│   ├─► get_remote_address(request)
│   ├─► Check rate limit
│   └─► raise RateLimitExceeded if exceeded
│
└─► Route Handler (WebSocket or HTTP)
```

---

## Frontend Startup Flow

### 1. Next.js Application Bootstrap

**File:** `nextjs/app/layout.tsx` → `nextjs/app/page.tsx`

```
Next.js App Router
│
├─► RootLayout component mounts
│   ├─► Load global CSS
│   ├─► Set metadata
│   └─► Render children
│
└─► Page component mounts
    └─► <IDE /> component
        │
        ├─► useWebSocketExecution()           # Initialize execution hook
        │   ├─► useState(outputLines)
        │   ├─► useState(isExecuting)
        │   ├─► useRef(wsRef)
        │   └─► Return {execute, sendInput, clearOutput}
        │
        ├─► useFileOperations()               # File operations hook
        │   └─► Return {saveFile, loadFile}
        │
        ├─► useEditorSettings()               # Editor settings hook
        │   ├─► useState(fontSize)
        │   ├─► useState(theme)
        │   └─► Return {fontSize, theme, ...}
        │
        └─► Render UI components
            ├─► <EditorToolbar />
            ├─► <CodeEditor />                 # Monaco Editor
            └─► <InteractiveTerminalOutput />  # Terminal display
```

### 2. Monaco Editor Initialization

**File:** `nextjs/app/components/CodeEditor.tsx`

```
<CodeEditor /> component mount
│
├─► @monaco-editor/react initialization
│   ├─► Load Monaco worker scripts
│   ├─► Initialize editor instance
│   ├─► Set language mode (from languageConfig)
│   ├─► Apply editorConfig settings
│   │   ├─► fontSize
│   │   ├─► theme
│   │   ├─► minimap
│   │   └─► tabSize
│   └─► Register onChange handler
│
└─► Ready to accept code input
```

---

## Code Execution Flow by Language

### Complete Execution Sequence (All Languages)

#### Phase 1: User Action to WebSocket Connection

```
User clicks "Run" button
│
├─► IDE.handleRun()
│   └─► execute(code, language)              # From useWebSocketExecution hook
│
└─► useWebSocketExecution.execute()
    ├─► setOutputLines([])                   # Clear output
    ├─► setIsExecuting(true)
    ├─► addOutputLine('system', 'Connecting...')
    │
    ├─► new WebSocket(wsUrl)                 # Create WebSocket
    │   └─► ws://localhost:8000/ws/execute (dev)
    │
    ├─► ws.onopen = () => {
    │   ├─► addOutputLine('system', 'Connected!')
    │   └─► ws.send({type: 'execute', code, language})
    │   }
    │
    └─► ws.onmessage = (event) => {...}      # Setup message handler
```

#### Phase 2: Backend WebSocket Handler

**File:** `backend/api/websocket.py`

```python
@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    │
    ├─► websocket.accept()                              # Accept connection
    │
    ├─► data = await websocket.receive_json()          # Wait for execute message
    │   └─► Validate: data.get("type") == "execute"
    │
    ├─► Extract: code, language
    │
    ├─► Generate filename
    │   ├─► get_executor(language)
    │   └─► filename_map.get(language)                 # main.py, main.js, etc.
    │
    ├─► CodeSubmission(code, language, filename)        # Pydantic validation
    │   ├─► validate_language()                         # Check if supported
    │   └─► validate_filename()                         # Check format
    │
    ├─► CodeValidator().validate(code, language)        # Security validation
    │   └─► [See Security Validation Flow below]
    │
    ├─► job_service.create_job(code, language, filename)
    │   └─► [See Job Creation Flow below]
    │
    ├─► manager.active_connections[job_id] = websocket  # Register connection
    │
    ├─► input_queue = asyncio.Queue()                  # Create input queue
    │
    ├─► pubsub_service.subscribe_to_channels(job_id, handler)
    │   └─► [See Pub/Sub Subscription Flow below]
    │
    ├─► execution_service.execute_job_streaming(job_id, input_queue)
    │   └─► [See Execution Flow below]
    │
    └─► while True:                                    # Listen for user input
        ├─► message = await websocket.receive_json()
        ├─► if message.type == "input":
        │   └─► input_queue.put(message.data)
        └─► Loop until disconnect
```

#### Phase 3: Security Validation Flow

**File:** `backend/api/security/validator.py`

```python
CodeValidator.validate(code, language)
│
├─► validator = CodeValidator()
│   ├─► TreeSitterParser.__init__()           # Initialize tree-sitter
│   ├─► PythonASTValidator.__init__()
│   ├─► JavaScriptASTValidator.__init__()
│   ├─► CCppASTValidator.__init__()
│   └─► RustASTValidator.__init__()
│
└─► Dispatch based on language:
    │
    ├─► if language == 'python':
    │   └─► python_validator.validate(code)
    │       ├─► ast.parse(code)                        # Parse Python AST
    │       ├─► ast.walk(tree)                         # Walk AST nodes
    │       ├─► Check for blocked operations
    │       │   ├─► PYTHON_BLOCKED_OPERATIONS
    │       │   └─► PYTHON_BLOCKED_MODULES
    │       └─► return (is_valid, error_message)
    │
    ├─► if language == 'javascript':
    │   └─► js_validator.validate(tree, code)
    │       ├─► ts_parser.parse(code, 'javascript')   # Tree-sitter parse
    │       ├─► tree.root_node.walk()                 # Walk syntax tree
    │       ├─► Check for:
    │       │   ├─► JAVASCRIPT_BLOCKED_OPERATIONS
    │       │   ├─► JAVASCRIPT_BLOCKED_MODULES
    │       │   ├─► JAVASCRIPT_DANGEROUS_PATTERNS
    │       │   └─► JAVASCRIPT_BLOCKED_IDENTIFIERS
    │       └─► return (is_valid, error_message)
    │
    ├─► if language in ['c', 'cpp']:
    │   └─► c_validator.validate(tree, code)
    │       ├─► ts_parser.parse(code, 'cpp')
    │       ├─► tree.root_node.walk()
    │       ├─► Check for:
    │       │   ├─► C_CPP_BLOCKED_FUNCTIONS
    │       │   └─► C_CPP_BLOCKED_HEADERS
    │       └─► return (is_valid, error_message)
    │
    └─► if language == 'rust':
        └─► rust_validator.validate(tree, code)
            ├─► ts_parser.parse(code, 'rust')
            ├─► tree.root_node.walk()
            ├─► Check for:
            │   └─► RUST_BLOCKED_OPERATIONS
            └─► return (is_valid, error_message)
```

#### Phase 4: Job Creation Flow

**File:** `backend/api/services/job_service.py`

```python
job_service.create_job(code, language, filename)
│
├─► job_id = str(uuid.uuid4())                        # Generate unique ID
│
├─► created_at = str(time.time())
│
├─► job_data = {                                       # Prepare metadata
│   "job_id": job_id,
│   "code": code,
│   "language": language,
│   "filename": filename,
│   "status": "queued",
│   "created_at": created_at
│   }
│
├─► job_key = f"job:{job_id}"                         # Redis key
│
├─► redis.hset(job_key, mapping=job_data)             # Store in Redis Hash
│
├─► redis.expire(job_key, redis_ttl)                  # Set TTL (1 hour)
│
└─► return job_id
```

#### Phase 5: Pub/Sub Subscription Flow

**File:** `backend/api/services/pubsub_service.py`

```python
pubsub_service.subscribe_to_channels(job_id, on_message)
│
├─► redis = await get_async_redis()
│
├─► pubsub = redis.pubsub()                           # Create Pub/Sub client
│
├─► channels = [
│   f"job:{job_id}:output",                           # Output stream
│   f"job:{job_id}:complete"                          # Completion event
│   ]
│
├─► pubsub.subscribe(*channels)                       # Subscribe to channels
│
└─► async for message in pubsub.listen():             # Listen for messages
    ├─► if message["type"] == "message":
    │   ├─► data = json.loads(message["data"])
    │   ├─► await on_message(data)                    # Forward to WebSocket
    │   └─► if data["type"] == "complete": break
    └─► Loop until complete
```

#### Phase 6: Execution Service Flow

**File:** `backend/api/services/execution_service.py`

```python
execution_service.execute_job_streaming(job_id, async_input_queue)
│
├─► job = await job_service.get_job(job_id)           # Fetch job data
│
├─► await job_service.mark_processing(job_id)          # Update status
│
├─► executor = await asyncio.to_thread(get_executor, job.language)
│   └─► [See Executor Creation Flow below]
│
├─► sync_input_queue = queue.Queue()                  # Thread-safe queue
│
├─► bridge_task = asyncio.create_task(bridge_input()) # Bridge async→sync queues
│   └─► while True:
│       ├─► item = await async_input_queue.get()
│       └─► sync_input_queue.put(item)
│
├─► def on_output(data: bytes):                       # Output callback
│   └─► asyncio.run_coroutine_threadsafe(
│       pubsub_service.publish_output(job_id, "stdout", data)
│       )
│
├─► result = await asyncio.to_thread(                 # Execute in thread pool
│   executor.execute,
│   code=job.code,
│   filename=job.filename,
│   on_output=on_output,
│   input_queue=sync_input_queue
│   )
│   └─► [See Executor Execute Flow below]
│
├─► bridge_task.cancel()                              # Stop input bridge
│
├─► await job_service.mark_completed(job_id, result)   # Update job status
│
└─► await pubsub_service.publish_complete(             # Publish completion
    job_id, result["exit_code"], result["execution_time"]
    )
```

#### Phase 7: Executor Creation Flow

**File:** `backend/executors/__init__.py`

```python
get_executor(language)
│
├─► language = language.lower().strip()
│
├─► executor_class = EXECUTORS.get(language)
│   │
│   ├─► 'python'     → PythonExecutor
│   ├─► 'javascript' → JavaScriptExecutor
│   ├─► 'c'          → CExecutor
│   ├─► 'cpp'/'c++'  → CppExecutor
│   └─► 'rust'       → RustExecutor
│
├─► if not executor_class:
│   └─► raise ValueError(f"Unsupported language: {language}")
│
└─► return executor_class()
    └─► BaseExecutor.__init__()
        ├─► settings = get_settings()
        ├─► self.timeout = settings.execution_timeout
        ├─► self.maxMemory = settings.max_memory_mb
        └─► self.maxFileSize = settings.max_file_size_mb
```

---

## Language-Specific Execution Flows

### Python Execution

**File:** `backend/executors/python.py` + `base.py`

```python
executor.execute(code, filename, on_output, input_queue)
│
├─► tempfile.TemporaryDirectory()                     # Create temp dir
│
├─► filepath = _writeToFile(tmpdir, code, filename)
│   ├─► _validateFileName(filename)                   # Validate filename
│   │   ├─► re.match(r'^[a-zA-Z0-9_.-]+$')
│   │   └─► Check for '..' and '/'
│   ├─► filepath = os.path.join(tmpdir, filename)
│   └─► open(filepath, 'w').write(code)               # Write code to file
│
├─► command = _build_command(filepath, tmpdir)
│   └─► PythonExecutor._build_command()
│       └─► return ['python3', filepath]
│
└─► _execute_pty(command, tmpdir, on_output, input_queue)
    │
    ├─► import pty, select, fcntl, termios
    │
    ├─► master_fd, slave_fd = pty.openpty()           # Create PTY
    │
    ├─► Set terminal size (24x80)
    │   └─► fcntl.ioctl(slave_fd, TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
    │
    ├─► sandbox_command = _build_sandbox_command(command, tmpdir)
    │   └─► ['/usr/bin/firejail',
    │        '--profile=/etc/firejail/sandbox.profile',
    │        '--private={tmpdir}',
    │        '--net=none',
    │        '--nodbus',
    │        '--noroot',
    │        '--rlimit-as={maxMemory * 1024 * 1024}',
    │        '--rlimit-cpu={timeout}',
    │        '--rlimit-fsize={maxFileSize * 1024 * 1024}',
    │        '--timeout=00:00:{timeout:02d}',
    │        'python3', filepath]
    │
    ├─► process = subprocess.Popen(
    │   sandbox_command,
    │   stdin=slave_fd,
    │   stdout=slave_fd,
    │   stderr=slave_fd,
    │   cwd=tmpdir,
    │   preexec_fn=os.setsid
    │   )
    │
    ├─► os.close(slave_fd)                            # Close slave, keep master
    │
    ├─► Set master_fd to non-blocking
    │   └─► fcntl.fcntl(master_fd, fcntl.F_SETFL, O_NONBLOCK)
    │
    └─► Main PTY loop:
        while True:
            │
            ├─► return_code = process.poll()           # Check if process done
            │   └─► if not None: break
            │
            ├─► Check for PTY output:
            │   ├─► readable, _, _ = select.select([master_fd], [], [], 0.01)
            │   └─► if master_fd in readable:
            │       ├─► data = os.read(master_fd, 4096)
            │       ├─► complete_output += data
            │       └─► on_output(data)                # Stream to WebSocket
            │
            ├─► Check for user input:
            │   ├─► user_input = input_queue.get_nowait()
            │   └─► os.write(master_fd, user_input.encode())
            │
            └─► Check timeout:
                └─► if time > timeout: process.kill()

        return {
            "success": returncode == 0,
            "exit_code": returncode,
            "execution_time": elapsed,
            "stdout": complete_output.decode(),
            "stderr": ""
        }
```

### JavaScript Execution

**File:** `backend/executors/javascript.py`

```python
JavaScriptExecutor._build_command(filepath, tmpdir)
│
└─► return ['node', filepath]
    │
    └─► [Rest of execution same as Python via BaseExecutor._execute_pty()]
```

### C Execution (Compiled Language)

**File:** `backend/executors/c.py` + `compiled_base.py`

```python
executor.execute(code, filename, on_output, input_queue)
│
├─► [Same temp dir and file writing as Python]
│
├─► command = _build_command(filepath, tmpdir)
│   │
│   └─► CompiledExecutor._build_command(filepath, tmpdir)
│       │
│       ├─► compiler, flags = _get_compiler_config()
│       │   └─► CExecutor._get_compiler_config()
│       │       └─► return ('gcc', ['-std=c11', '-lm'])
│       │
│       ├─► binarypath = os.path.join(tmpdir, 'program')
│       │
│       ├─► compile_result = subprocess.run(
│       │   ['gcc', filepath, '-o', binarypath, '-std=c11', '-lm'],
│       │   capture_output=True,
│       │   timeout=compilation_timeout  # 10 seconds
│       │   )
│       │
│       ├─► if returncode != 0:
│       │   └─► raise Exception(f"Compilation failed: {stderr}")
│       │
│       └─► return [binarypath]                        # Return compiled binary
│
└─► _execute_pty([binarypath], tmpdir, on_output, input_queue)
    └─► [Same PTY execution as Python, but runs binary instead]
```

### C++ Execution

**File:** `backend/executors/cpp.py`

```python
CppExecutor._get_compiler_config()
│
└─► return ('g++', ['-std=c++17'])                    # C++17 standard
    │
    └─► [Rest same as C via CompiledExecutor]
```

### Rust Execution

**File:** `backend/executors/rust.py`

```python
RustExecutor._get_compiler_config()
│
└─► return ('rustc', [])                              # No extra flags
    │
    └─► [Rest same as C via CompiledExecutor]
```

---

## Output Streaming Flow

### From PTY to Frontend

```
PTY process outputs: "Hello, World!\n"
│
├─► os.read(master_fd, 4096) in _execute_pty()
│   └─► data = b"Hello, World!\n"
│
├─► on_output(data)                                    # Callback from executor
│   └─► execution_service.on_output(data)
│       └─► asyncio.run_coroutine_threadsafe(
│           pubsub_service.publish_output(job_id, "stdout", data.decode())
│           )
│
├─► pubsub_service.publish_output(job_id, "stdout", "Hello, World!\n")
│   ├─► redis = await get_async_redis()
│   ├─► channel = f"job:{job_id}:output"
│   ├─► message = json.dumps({
│   │   "type": "output",
│   │   "stream": "stdout",
│   │   "data": "Hello, World!\n"
│   │   })
│   └─► await redis.publish(channel, message)
│
├─► Redis Pub/Sub broadcasts to subscribers
│
├─► pubsub_service.subscribe_to_channels() receives message
│   ├─► data = json.loads(message["data"])
│   └─► await on_message(data)
│
├─► websocket handler's on_message callback
│   └─► manager.send_message(job_id, data)
│       └─► websocket.send_json(data)
│
├─► Frontend WebSocket receives message
│   └─► ws.onmessage = (event) => {
│       ├─► message = JSON.parse(event.data)
│       └─► if message.type === 'output':
│           └─► addOutputLine(message.stream, message.data)
│           }
│
└─► Frontend updates terminal display
    └─► InteractiveTerminalOutput rerenders
        └─► Shows: "Hello, World!\n"
```

---

## Interactive Input Flow

### From Frontend to PTY

```
User types "Alice" and presses Enter in terminal
│
├─► InteractiveTerminalOutput.handleInputSubmit()
│   └─► sendInput("Alice")                            # From useWebSocketExecution hook
│
├─► useWebSocketExecution.sendInput("Alice")
│   ├─► ws.send(JSON.stringify({
│   │   type: 'input',
│   │   data: 'Alice\n'
│   │   }))
│   └─► addOutputLine('input', 'Alice')               # Echo to terminal
│
├─► Backend WebSocket receives message
│   └─► websocket_execute() message loop
│       ├─► message = await websocket.receive_json()
│       └─► if message.type == "input":
│           └─► input_queue.put("Alice\n")             # asyncio.Queue
│
├─► Input bridge transfers to sync queue
│   └─► bridge_input() task
│       ├─► item = await async_input_queue.get()      # "Alice\n"
│       └─► sync_input_queue.put(item)                 # queue.Queue
│
├─► PTY loop reads from sync queue
│   └─► _execute_pty() main loop
│       ├─► user_input = input_queue.get_nowait()     # "Alice\n"
│       └─► os.write(master_fd, user_input.encode())   # Write to PTY
│
├─► PTY forwards to process stdin
│
└─► Python code receives input:
    name = input("Enter name: ")                      # Gets "Alice"
```

---

## Completion Flow

```
Process exits with code 0
│
├─► _execute_pty() detects process finished
│   ├─► return_code = process.poll()  # Returns 0
│   └─► return {
│       "success": True,
│       "exit_code": 0,
│       "execution_time": 1.234,
│       "stdout": complete_output,
│       "stderr": ""
│       }
│
├─► execution_service.execute_job_streaming() receives result
│   ├─► await job_service.mark_completed(job_id, result)
│   │   ├─► redis.hset(f"job:{job_id}", "result", json.dumps(result))
│   │   ├─► redis.hset(f"job:{job_id}", "status", "completed")
│   │   └─► redis.hset(f"job:{job_id}", "completed_at", time.time())
│   │
│   └─► await pubsub_service.publish_complete(job_id, 0, 1.234)
│       ├─► channel = f"job:{job_id}:complete"
│       ├─► message = json.dumps({
│       │   "type": "complete",
│       │   "exit_code": 0,
│       │   "execution_time": 1.234
│       │   })
│       └─► await redis.publish(channel, message)
│
├─► Pub/Sub subscription receives completion
│   └─► pubsub_service.subscribe_to_channels()
│       ├─► data = json.loads(message)
│       ├─► await on_message(data)
│       └─► if data["type"] == "complete": break      # Exit subscription loop
│
├─► WebSocket handler forwards to frontend
│   └─► websocket.send_json({
│       "type": "complete",
│       "exit_code": 0,
│       "execution_time": 1.234
│       })
│
├─► Frontend receives completion
│   └─► ws.onmessage = (event) => {
│       ├─► message = JSON.parse(event.data)
│       └─► if message.type === 'complete':
│           ├─► addOutputLine('system', `Completed in ${time}s`)
│           ├─► setIsExecuting(false)
│           └─► ws.close()
│       }
│
└─► WebSocket connection closed
    └─► manager.disconnect(job_id)
        └─► Delete from active_connections
```

---

## Error Handling Flow

### Validation Error

```
Invalid code submitted (contains 'eval')
│
├─► CodeValidator.validate(code, language)
│   └─► return (False, "Code validation failed: 'eval' is blocked")
│
├─► websocket_execute() receives validation result
│   └─► if not is_valid:
│       ├─► await websocket.send_json({
│       │   "type": "error",
│       │   "message": "Code validation failed: 'eval' is blocked"
│       │   })
│       └─► await websocket.close()
│
└─► Frontend displays error
    └─► addOutputLine('stderr', error_message)
```

### Compilation Error

```
C code has syntax error
│
├─► CompiledExecutor._build_command()
│   ├─► subprocess.run(['gcc', ...])
│   └─► if returncode != 0:
│       └─► raise Exception(f"Compilation failed:\n{stderr}")
│
├─► execution_service catches exception
│   ├─► error_result = {
│   │   "success": False,
│   │   "stderr": "Compilation failed: ...",
│   │   "exit_code": -1
│   │   }
│   ├─► await job_service.mark_failed(job_id, error, error_result)
│   └─► await pubsub_service.publish_error(job_id, error)
│
└─► Frontend displays compilation error
```

### Runtime Timeout

```
Code runs longer than 7 seconds
│
├─► _execute_pty() timeout check
│   └─► if time.time() - start_time > self.timeout:
│       └─► process.kill()
│
├─► Process exits with signal (killed)
│   └─► return {
│       "success": False,
│       "exit_code": -9,  # SIGKILL
│       ...
│       }
│
└─► Completion message sent with exit_code=-9
```

---

## Summary of Key Function Chains

### Startup Chain
```
main.py
└─► lifespan()
    ├─► get_async_redis()
    └─► JobService.__init__()
```

### Execution Chain (Interpreted Language)
```
WebSocket.onopen
└─► websocket_execute()
    ├─► CodeValidator.validate()
    ├─► job_service.create_job()
    ├─► execution_service.execute_job_streaming()
    │   └─► executor.execute()
    │       ├─► _writeToFile()
    │       ├─► _build_command() → ['python3', 'main.py']
    │       └─► _execute_pty() → subprocess.Popen()
    └─► pubsub_service.subscribe_to_channels()
```

### Execution Chain (Compiled Language)
```
WebSocket.onopen
└─► websocket_execute()
    ├─► CodeValidator.validate()
    ├─► job_service.create_job()
    ├─► execution_service.execute_job_streaming()
    │   └─► executor.execute()
    │       ├─► _writeToFile()
    │       ├─► _build_command()
    │       │   ├─► subprocess.run(['gcc', ...])      # Compilation
    │       │   └─► return ['./program']
    │       └─► _execute_pty(['./program']) → subprocess.Popen()
    └─► pubsub_service.subscribe_to_channels()
```

### Output Streaming Chain
```
PTY process output
└─► os.read(master_fd)
    └─► on_output(data)
        └─► pubsub_service.publish_output()
            └─► redis.publish()
                └─► pubsub listener receives
                    └─► websocket.send_json()
                        └─► frontend.addOutputLine()
```

### Input Streaming Chain
```
User input in terminal
└─► sendInput()
    └─► WebSocket.send()
        └─► input_queue.put()
            └─► os.write(master_fd)
                └─► process stdin receives input
```
