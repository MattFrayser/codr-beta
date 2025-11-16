# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage of the code sandbox executor with **61 well-organized tests** across 9 files. The structure is designed for clarity, maintainability, and room to grow.

### Test Statistics

- **Total Tests:** 61
- **Test Files:** 9
- **Coverage:** ~75% of critical functionality
- **Runtime:** ~15-20 seconds

## Test Organization

### By Category

| Category | Tests | Files | Focus |
|----------|-------|-------|-------|
| **Executors** | 25 | 5 | One file per language (Python, JS, C, C++, Rust) |
| **Security** | 11 | 1 | Code validation and AST analysis |
| **Services** | 7 | 1 | Job lifecycle management |
| **Auth** | 7 | 1 | API key validation and middleware |
| **Integration** | 11 | 1 | End-to-end flows |
| **TOTAL** | **61** | **9** | |

## File Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── README.md                      # This file
│
├── unit/
│   ├── executors/
│   │   ├── test_python.py        # 5 tests - Python execution
│   │   ├── test_javascript.py    # 5 tests - JavaScript execution
│   │   ├── test_c.py             # 5 tests - C compilation and execution
│   │   ├── test_cpp.py           # 5 tests - C++ compilation and execution
│   │   └── test_rust.py          # 5 tests - Rust compilation and execution
│   │
│   ├── security/
│   │   └── test_validation.py    # 11 tests - Security validation
│   │
│   ├── services/
│   │   └── test_job_service.py   # 7 tests - Job lifecycle
│   │
│   └── middleware/
│       └── test_auth.py          # 7 tests - Authentication
│
└── integration/
    └── test_execution.py         # 11 tests - End-to-end flows
```

## Running Tests

### Run All Tests

```bash
# From backend directory
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=. --cov-report=html
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
# Python executor tests only
pytest tests/unit/executors/test_python.py

# JavaScript executor tests only
pytest tests/unit/executors/test_javascript.py

# C executor tests only
pytest tests/unit/executors/test_c.py

# C++ executor tests only
pytest tests/unit/executors/test_cpp.py

# Rust executor tests only
pytest tests/unit/executors/test_rust.py
```

## Test Coverage

### Executor Tests (25 tests)

Each language has 5 tests covering:
- ✅ Command building
- ✅ Filename validation
- ✅ Path traversal prevention
- ✅ Compiler configuration (for compiled languages)
- ✅ Special character blocking

### Security Tests (11 tests)

- ✅ Blocking dangerous Python functions (eval, exec)
- ✅ Blocking dangerous Python modules (os, subprocess)
- ✅ Blocking dangerous JavaScript modules (fs, child_process)
- ✅ Allowing safe code
- ✅ Validator dispatch

### Service Tests (7 tests)

- ✅ Job creation with UUID
- ✅ Job retrieval
- ✅ Status updates (queued → processing → completed)
- ✅ Job existence checks
- ✅ Complete job lifecycle
- ✅ Failed job handling

### Auth Tests (7 tests)

- ✅ Valid/invalid/missing API key handling
- ✅ Constant-time comparison (timing attack prevention)
- ✅ Health endpoint exclusion
- ✅ Docs endpoint exclusion
- ✅ Protected endpoint verification

### Integration Tests (11 tests)

- ✅ Filename validation in executor
- ✅ Validator dispatch for multiple languages
- ✅ Executor factory pattern
- ✅ Complete job lifecycle
- ✅ Job creation for all languages

## Adding New Tests

### For a New Language

1. Create `tests/unit/executors/test_<language>.py`
2. Add 5 tests: command building, filename validation, path traversal, special chars, compiler config
3. Add fixture to `conftest.py`

### For Security Rules

Add to `tests/unit/security/test_validation.py`

### For New Features

- Service tests → `tests/unit/services/`
- Integration tests → `tests/integration/`
- Security tests → `tests/unit/security/`

## Daily Workflow

```bash
# Before starting work
pytest

# Before committing
pytest -v

# Before deploying
pytest --cov=. --cov-report=html
```

## Summary

✅ **61 tests** covering critical functionality
✅ **One file per language** for easy growth
✅ **15-20 second** runtime
✅ **~75% coverage** of critical paths
✅ **Well-organized** by category and function

This suite balances comprehensive testing with maintainability perfect for solo developers.
