# Codr Testing Guide

Complete guide to testing the Codr code execution platform.

## Test Suite Overview

The Codr project has a well-organized test suite covering critical functionality:

- ✅ **61 focused tests** - Organized by language and component
- ✅ **9 test files** - One per language + core functionality
- ✅ **~75% code coverage** - Critical paths thoroughly tested
- ✅ **15-20 second runtime** - Fast feedback for daily development
- ✅ **Mock Redis** - No external dependencies for unit tests
- ✅ **Room to grow** - Easy to add tests without reorganization

## Quick Start

```bash
# 1. Install test dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Run all tests
pytest

# 3. Run with coverage
pytest --cov=. --cov-report=html

# 4. View coverage report
open htmlcov/index.html
```

## Test Organization

```
backend/tests/
├── conftest.py                    # Shared fixtures (61 fixtures)
├── pytest.ini                     # Pytest configuration
├── README.md                      # Detailed testing guide
│
├── unit/
│   ├── executors/                 # 25 tests (5 per language)
│   │   ├── test_python.py         # Python executor
│   │   ├── test_javascript.py     # JavaScript executor
│   │   ├── test_c.py              # C compiler/executor
│   │   ├── test_cpp.py            # C++ compiler/executor
│   │   └── test_rust.py           # Rust compiler/executor
│   │
│   ├── security/                  # 11 tests
│   │   └── test_validation.py     # AST validation, blocklists
│   │
│   ├── services/                  # 7 tests
│   │   └── test_job_service.py    # Job lifecycle management
│   │
│   └── middleware/                # 7 tests
│       └── test_auth.py           # API key authentication
│
└── integration/                   # 11 tests
    └── test_execution.py          # End-to-end flows
```

**Total: 61 tests across 9 files**

## What's Tested

### ✅ Executors (25 tests - 5 per language)

Each language (Python, JavaScript, C, C++, Rust) has tests for:
- Command building
- Filename validation
- Path traversal prevention
- Compiler configuration (compiled languages)
- Special character blocking

**Files:**
- `tests/unit/executors/test_python.py`
- `tests/unit/executors/test_javascript.py`
- `tests/unit/executors/test_c.py`
- `tests/unit/executors/test_cpp.py`
- `tests/unit/executors/test_rust.py`

### ✅ Security Validators (11 tests)

**Python Security:**
- Block eval() function
- Block exec() function
- Block os module
- Block subprocess module
- Allow safe code
- Allow safe imports

**JavaScript Security:**
- Block require('fs')
- Block require('child_process')
- Allow safe code

**Validator Dispatch:**
- Correct language routing
- Error handling

**File:** `tests/unit/security/test_validation.py`

### ✅ Services (7 tests)

**Job Service:**
- Create job with UUID
- Retrieve job metadata
- Mark job as processing
- Mark job as completed
- Check job existence
- Complete job lifecycle
- Handle failed jobs

**File:** `tests/unit/services/test_job_service.py`

### ✅ Authentication (7 tests)

**Auth Middleware:**
- Accept valid API key
- Reject invalid API key (403)
- Reject missing API key (403)
- Use constant-time comparison (timing attack prevention)
- Exclude /health endpoint
- Exclude /docs endpoints
- Protect API endpoints

**File:** `tests/unit/middleware/test_auth.py`

### ✅ Integration Tests (11 tests)

**End-to-End Flows:**
- Filename validation in executor
- Valid filename acceptance
- Validator dispatch to Python
- Validator dispatch to JavaScript
- Safe code validation
- Python executor factory
- JavaScript executor factory
- C executor factory
- Unsupported language error
- Complete job lifecycle
- Job creation for all languages

**File:** `tests/integration/test_execution.py`

## Running Tests

### Run All Tests

```bash
# Standard run
pytest

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

### Run by Category

```bash
# All executor tests
pytest tests/unit/executors/

# All security tests
pytest tests/unit/security/

# All service tests
pytest tests/unit/services/

# All auth tests
pytest tests/unit/middleware/

# All integration tests
pytest tests/integration/
```

### Run by Language

```bash
# Python tests only
pytest tests/unit/executors/test_python.py

# JavaScript tests only
pytest tests/unit/executors/test_javascript.py

# C tests only
pytest tests/unit/executors/test_c.py

# C++ tests only
pytest tests/unit/executors/test_cpp.py

# Rust tests only
pytest tests/unit/executors/test_rust.py
```

### Run Specific Test

```bash
# Single test function
pytest tests/unit/executors/test_python.py::TestPythonExecutor::test_builds_correct_command

# All tests in a class
pytest tests/unit/security/test_validation.py::TestPythonSecurityValidation

# By pattern
pytest -k "test_blocks"
pytest -k "test_python"
```

### Run with Markers

```bash
# Async tests only
pytest -m asyncio

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration
```

## Test Coverage

### Generate Coverage Report

```bash
# HTML report (most useful)
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=. --cov-report=term-missing

# XML report (for CI/CD)
pytest --cov=. --cov-report=xml
```

### Current Coverage

- **Overall:** ~75%
- **Executors:** ~80%
- **Security:** ~90%
- **Services:** ~85%
- **Auth:** ~75%
- **Integration:** ~70%

## Adding New Tests

### For a New Language

1. Create `tests/unit/executors/test_<language>.py`

```python
"""
Tests for <Language> Executor

Covers:
- Command building
- Filename validation
- Compilation (if applicable)
"""

import pytest
from executors.<language> import <Language>Executor


class Test<Language>Executor:
    """Test suite for <Language> code execution"""

    def test_builds_correct_command(self, <language>_executor):
        """Should build correct <compiler/interpreter> command"""
        command = <language>_executor._build_command("/tmp/test.<ext>", "/tmp")
        assert command == ["<compiler>", "/tmp/test.<ext>"]

    def test_validates_filename_format(self, <language>_executor):
        """Should validate filename follows allowed format"""
        <language>_executor._validateFileName("test.<ext>")

    def test_blocks_path_traversal(self, <language>_executor):
        """Should block path traversal attempts"""
        with pytest.raises(ValueError, match="Invalid filename"):
            <language>_executor._validateFileName("../hack.<ext>")

    # Add 2-3 more tests as needed
```

2. Add fixture to `conftest.py`:

```python
@pytest.fixture
def <language>_executor():
    """Provide <Language>Executor instance"""
    from executors.<language> import <Language>Executor
    return <Language>Executor()
```

### For Security Rules

Add to `tests/unit/security/test_validation.py`:

```python
def test_blocks_dangerous_operation(self, code_validator):
    """Should block dangerous operation X"""
    malicious_code = """
    // dangerous code
    """
    is_valid, error = code_validator.validate(malicious_code, "language")
    assert is_valid is False
```

### For New Features

- **Service tests:** Add to `tests/unit/services/test_job_service.py`
- **Integration tests:** Add to `tests/integration/test_execution.py`
- **Security tests:** Add to `tests/unit/security/test_validation.py`

## Test Fixtures

All fixtures are defined in `conftest.py`. Key fixtures:

### Executors
- `python_executor`, `javascript_executor`, `c_executor`, `cpp_executor`, `rust_executor`

### Services
- `job_service`, `pubsub_service`, `execution_service`

### Validators
- `code_validator`, `python_validator`

### Data
- `sample_python_code`, `sample_javascript_code`, `sample_c_code`, `sample_cpp_code`, `sample_rust_code`
- `malicious_python_code`, `malicious_javascript_code`

### Mocks
- `mock_redis`, `mock_websocket`, `mock_subprocess`

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt
      - name: Run tests
        run: |
          cd backend
          pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Daily Workflow

```bash
# Morning - Quick health check
pytest

# During development - Test specific component
pytest tests/unit/executors/test_python.py -v

# Before commit - Run all tests
pytest -v

# Before deployment - Full suite with coverage
pytest --cov=. --cov-report=html
```

## Best Practices

### DO ✅

- Run tests before every commit
- Write tests when adding features
- Fix failing tests immediately
- Use descriptive test names
- Test error cases, not just happy paths
- Keep tests fast (mock external dependencies)
- Group related tests in classes

### DON'T ❌

- Skip failing tests
- Test third-party library behavior
- Make tests dependent on each other
- Use sleep() in tests (use async properly)
- Ignore warnings
- Duplicate test logic

## Troubleshooting

### Tests Failing

```bash
# Verbose output
pytest -v

# Show stdout/stderr
pytest -s

# Stop on first failure
pytest -x

# Run specific failing test
pytest tests/path/to/test.py::test_name -vv
```

### Import Errors

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Async Test Errors

Ensure `pytest.ini` has:
```ini
asyncio_mode = auto
```

And `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

### Coverage Not Showing

```bash
# Install coverage
pip install pytest-cov

# Run with coverage
pytest --cov=. --cov-report=html

# Open report
open htmlcov/index.html
```

## Summary

The Codr test suite provides:

✅ **61 focused tests** covering critical functionality
✅ **9 organized files** - one per language + core components
✅ **~75% coverage** of critical paths
✅ **15-20 second** runtime for fast feedback
✅ **Easy to extend** - clear patterns for adding tests
✅ **Well-documented** - README.md in tests/ directory

**Perfect for solo developers:** Balances thorough testing with maintainability. Focus on critical paths, not exhaustive edge cases.

For detailed testing information, see `backend/tests/README.md`.
