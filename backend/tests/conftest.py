"""
Pytest fixtures and configuration for the entire test suite

This file contains shared fixtures used across all tests.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
from unittest.mock import AsyncMock, MagicMock

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set test environment variables
os.environ["ENV"] = "testing"
os.environ["API_KEY"] = "test-api-key-12345"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["EXECUTION_TIMEOUT"] = "5"


# ============================================================================
# Async fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Settings fixtures
# ============================================================================

@pytest.fixture
def test_settings():
    """Provide test settings"""
    from lib.config.settings import AppSettings

    return AppSettings(
        env="testing",
        api_key="test-api-key-12345",
        jwt_secret="test-secret-key-for-testing",
        host="127.0.0.1",
        port=8000,
        execution_timeout=5,
        max_memory_mb=100,
        max_file_size_mb=1,
        compilation_timeout=10,
        redis_url="redis://localhost:6379/1",
        redis_ttl=3600,
    )


# ============================================================================
# Redis fixtures
# ============================================================================

@pytest.fixture
async def mock_redis():
    """Provide a mock Redis client"""
    import fakeredis.aioredis

    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()
    await redis.close()


@pytest.fixture
async def redis_client(mock_redis):
    """Alias for mock_redis for clearer naming"""
    return mock_redis


# ============================================================================
# Service fixtures
# ============================================================================

@pytest.fixture
async def job_service(redis_client):
    """Provide JobService instance with mock Redis"""
    from lib.services.job_service import JobService

    service = JobService(redis_client)
    return service


@pytest.fixture
def pubsub_service():
    """Provide PubSubService instance"""
    from lib.services.pubsub_service import PubSubService

    return PubSubService()


# ============================================================================
# Executor fixtures
# ============================================================================

@pytest.fixture
def python_executor():
    """Provide PythonExecutor instance"""
    from lib.executors.python import PythonExecutor

    return PythonExecutor()


@pytest.fixture
def javascript_executor():
    """Provide JavaScriptExecutor instance"""
    from lib.executors.javascript import JavaScriptExecutor

    return JavaScriptExecutor()


@pytest.fixture
def c_executor():
    """Provide CExecutor instance"""
    from lib.executors.c import CExecutor

    return CExecutor()


@pytest.fixture
def cpp_executor():
    """Provide CppExecutor instance"""
    from lib.executors.cpp import CppExecutor

    return CppExecutor()


@pytest.fixture
def rust_executor():
    """Provide RustExecutor instance"""
    from lib.executors.rust import RustExecutor

    return RustExecutor()


# ============================================================================
# Validator fixtures
# ============================================================================

@pytest.fixture
def code_validator():
    """Provide CodeValidator instance"""
    from lib.security.validator import CodeValidator

    return CodeValidator()


@pytest.fixture
def python_validator():
    """Provide PythonASTValidator instance"""
    from lib.security.python_ast_validator import PythonASTValidator

    return PythonASTValidator()


# ============================================================================
# Test data fixtures
# ============================================================================

@pytest.fixture
def sample_python_code():
    """Provide sample Python code"""
    return """
def hello():
    print("Hello, World!")
    return 42

hello()
"""


@pytest.fixture
def sample_javascript_code():
    """Provide sample JavaScript code"""
    return """
function hello() {
    console.log("Hello, World!");
    return 42;
}

hello();
"""


@pytest.fixture
def sample_c_code():
    """Provide sample C code"""
    return """
#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
"""


@pytest.fixture
def sample_cpp_code():
    """Provide sample C++ code"""
    return """
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
"""


@pytest.fixture
def sample_rust_code():
    """Provide sample Rust code"""
    return """
fn main() {
    println!("Hello, World!");
}
"""


@pytest.fixture
def malicious_python_code():
    """Provide malicious Python code for security testing"""
    return """
import os
os.system("ls /")
"""


@pytest.fixture
def malicious_javascript_code():
    """Provide malicious JavaScript code for security testing"""
    return """
const fs = require('fs');
fs.readFileSync('/etc/passwd');
"""


# ============================================================================
# Mock fixtures
# ============================================================================

@pytest.fixture
def mock_subprocess():
    """Mock subprocess for executor testing"""
    from unittest.mock import Mock, patch

    mock_process = Mock()
    mock_process.poll.return_value = 0
    mock_process.returncode = 0

    with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
        yield mock_popen


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for WebSocket testing"""
    from unittest.mock import AsyncMock

    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_json = AsyncMock()
    websocket.close = AsyncMock()
    websocket.client = ("127.0.0.1", 12345)
    websocket.headers = {}

    return websocket


# ============================================================================
# Temporary directory fixtures
# ============================================================================

@pytest.fixture
def temp_code_file(tmp_path):
    """Create a temporary code file"""
    def _create_file(code: str, filename: str = "test.py"):
        file_path = tmp_path / filename
        file_path.write_text(code)
        return str(file_path)

    return _create_file
