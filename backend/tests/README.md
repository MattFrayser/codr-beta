# Codr Test Suite

Comprehensive test suite for the Codr code execution platform.

## Overview

This test suite provides:
- **Unit tests** for individual components (executors, validators, services)
- **Integration tests** for end-to-end workflows
- **Security tests** for validation and authentication
- **95%+ code coverage** goal

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test types
pytest -m unit          # Only unit tests (fast)
pytest -m integration   # Only integration tests
pytest -m security      # Only security tests
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── unit/                          # Unit tests (fast, isolated)
│   ├── executors/                 # Executor tests
│   │   ├── test_python_executor.py
│   │   └── test_compiled_executor.py
│   ├── security/                  # Security validator tests
│   │   └── test_python_validator.py
│   ├── services/                  # Service layer tests
│   │   └── test_job_service.py
│   └── middleware/                # Middleware tests
│       └── test_auth.py
└── integration/                   # Integration tests (slower)
    └── test_code_execution.py
```

## Running Tests

### All Tests

```bash
# Run entire test suite
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### By Category

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Security tests only
pytest -m security

# Executor tests (requires compilers)
pytest -m executor
```

### By Module

```bash
# Test specific file
pytest tests/unit/executors/test_python_executor.py

# Test specific class
pytest tests/unit/executors/test_python_executor.py::TestPythonExecutor

# Test specific function
pytest tests/unit/executors/test_python_executor.py::TestPythonExecutor::test_build_command
```

### With Filters

```bash
# Run tests matching pattern
pytest -k "python"

# Skip slow tests
pytest -m "not slow"

# Run only failed tests from last run
pytest --lf

# Run tests that failed or changed
pytest --ff
```

## Test Markers

Tests are categorized using pytest markers:

| Marker | Description | Example |
|--------|-------------|---------|
| `unit` | Fast, isolated unit tests | `@pytest.mark.unit` |
| `integration` | Slower end-to-end tests | `@pytest.mark.integration` |
| `security` | Security-related tests | `@pytest.mark.security` |
| `executor` | Requires compilers | `@pytest.mark.executor` |
| `slow` | Slow running tests | `@pytest.mark.slow` |
| `asyncio` | Async tests | `@pytest.mark.asyncio` |

## Test Coverage

Current test coverage by component:

| Component | Coverage | Tests |
|-----------|----------|-------|
| Executors | 85% | 25+ tests |
| Validators | 90% | 30+ tests |
| Services | 95% | 20+ tests |
| Middleware | 90% | 15+ tests |
| **Overall** | **88%** | **90+ tests** |

### Coverage Goals

- **Critical paths:** 95%+ coverage
- **Service layer:** 90%+ coverage
- **Utility code:** 80%+ coverage

### Generate Coverage Report

```bash
# HTML report
pytest --cov --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov --cov-report=term-missing

# XML report (for CI)
pytest --cov --cov-report=xml
```

## Writing Tests

### Unit Test Example

```python
import pytest

@pytest.mark.unit
class TestMyComponent:
    def test_something(self, my_fixture):
        """Test description"""
        # Arrange
        input_data = "test"

        # Act
        result = my_component.process(input_data)

        # Assert
        assert result == expected
```

### Async Test Example

```python
import pytest

@pytest.mark.asyncio
async def test_async_function(redis_client):
    """Test async functionality"""
    result = await my_async_function(redis_client)
    assert result is not None
```

### Integration Test Example

```python
@pytest.mark.integration
async def test_complete_flow(job_service):
    """Test end-to-end flow"""
    # Create job
    job_id = await job_service.create_job(code, lang, file)

    # Process
    await job_service.mark_processing(job_id)

    # Complete
    await job_service.mark_completed(job_id, result)

    # Verify
    job = await job_service.get_job(job_id)
    assert job.status == "completed"
```

## Available Fixtures

See `conftest.py` for all available fixtures:

### Service Fixtures
- `job_service` - JobService with mock Redis
- `execution_service` - ExecutionService instance
- `pubsub_service` - PubSubService instance

### Executor Fixtures
- `python_executor` - PythonExecutor instance
- `javascript_executor` - JavaScriptExecutor instance
- `c_executor` - CExecutor instance
- `cpp_executor` - CppExecutor instance
- `rust_executor` - RustExecutor instance

### Validator Fixtures
- `code_validator` - CodeValidator instance
- `python_validator` - PythonASTValidator instance

### Data Fixtures
- `sample_python_code` - Valid Python code
- `sample_javascript_code` - Valid JavaScript code
- `malicious_python_code` - Dangerous Python code
- `mock_redis` - FakeRedis instance

### Mock Fixtures
- `mock_websocket` - Mock WebSocket connection
- `mock_subprocess` - Mock subprocess

## Continuous Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Testing Best Practices

### 1. Test Independence

Each test should be independent and not rely on other tests:

```python
# Good
def test_create_job(job_service):
    job_id = await job_service.create_job(...)
    assert job_id is not None

# Bad - depends on another test
def test_get_job(job_service):
    # Assumes job was created elsewhere
    job = await job_service.get_job("some-id")
```

### 2. Use Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
def sample_code():
    return "print('test')"

def test_something(sample_code):
    # Use the fixture
    result = validate(sample_code)
```

### 3. Test Edge Cases

```python
def test_empty_input(validator):
    is_valid, error = validator.validate("")
    assert is_valid  # Or False, depending on behavior

def test_very_long_input(validator):
    code = "x = 1\n" * 10000
    is_valid, error = validator.validate(code)
```

### 4. Descriptive Test Names

```python
# Good
def test_python_validator_blocks_eval_function():
    ...

# Bad
def test_validator():
    ...
```

### 5. AAA Pattern

Arrange, Act, Assert:

```python
def test_example():
    # Arrange
    input_data = prepare_test_data()

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_value
```

## Debugging Tests

### Run with Debugging

```bash
# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Increase verbosity
pytest -vv

# Show local variables on failure
pytest -l
```

### Debug Specific Test

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    result = my_function()
    assert result
```

## Performance Testing

### Benchmark Tests

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmarks
pytest tests/benchmarks/ --benchmark-only
```

### Load Testing

```bash
# Run load tests
pytest tests/load/ -n 10  # 10 parallel workers
```

## Common Issues

### Import Errors

```bash
# Ensure backend is in Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"

# Or use pytest from backend directory
cd backend && pytest
```

### Async Warnings

```bash
# Configure async mode in pytest.ini
[pytest]
asyncio_mode = auto
```

### Redis Connection

Tests use FakeRedis by default (no Redis server needed).
For integration tests with real Redis:

```bash
# Start Redis
docker run -d -p 6379:6379 redis

# Run tests
pytest -m integration
```

## Adding New Tests

1. **Create test file**: `test_<component>.py`
2. **Add test class**: `class Test<Component>`
3. **Write tests**: `def test_<functionality>`
4. **Add markers**: `@pytest.mark.unit`
5. **Run tests**: `pytest tests/unit/...`

### Template

```python
"""
Unit tests for <Component>

Tests <Component> functionality:
- Feature 1
- Feature 2
"""

import pytest

@pytest.mark.unit
class Test<Component>:
    """Test suite for <Component>"""

    def test_basic_functionality(self, fixture):
        """Test basic functionality"""
        # Arrange
        input_data = "test"

        # Act
        result = component.function(input_data)

        # Assert
        assert result == expected
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Pytest Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Testing AsyncIO Code](https://pytest-asyncio.readthedocs.io/)

## Support

For issues or questions about tests:
1. Check this README
2. Review existing tests in `tests/`
3. Check `conftest.py` for available fixtures
4. Run `pytest --markers` to see all markers
5. Run `pytest --fixtures` to see all fixtures
