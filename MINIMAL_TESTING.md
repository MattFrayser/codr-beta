# Minimal Test Suite Guide

## Overview

The minimal test suite contains **25 essential tests** that cover ~75% of critical functionality. This suite is designed for **solo developer daily use** with fast feedback and low maintenance overhead.

## Why Use the Minimal Suite?

**Problem:** The full test suite (90+ tests) is comprehensive but:
- Takes ~30 seconds to run
- Requires significant maintenance
- Can be overwhelming for daily development
- Too much overhead for quick iterations

**Solution:** The minimal suite gives you:
- ✅ **Fast feedback** (~15 seconds)
- ✅ **75% coverage** of critical paths
- ✅ **Low maintenance** (single file)
- ✅ **Daily confidence** in core functionality

## Quick Start

### Run the Minimal Suite

```bash
# From backend directory
cd backend

# Fast run (no coverage)
pytest -c pytest-minimal.ini tests/test_minimal.py

# With simple output
pytest tests/test_minimal.py -v --tb=short

# Run specific category
pytest tests/test_minimal.py -k executor    # Only executor tests
pytest tests/test_minimal.py -k security    # Only security tests
pytest tests/test_minimal.py -k auth        # Only auth tests
```

### Run the Full Suite (Before Deployment)

```bash
# Run all 90+ tests with coverage
pytest

# Run full suite with verbose output
pytest -v

# Run by category
pytest -m unit          # All unit tests
pytest -m integration   # All integration tests
pytest -m security      # All security tests
```

## What's Covered?

### 25 Tests Breakdown

| Category | Tests | Coverage |
|----------|-------|----------|
| **Executor Smoke Tests** | 5 | Python, JS, C, C++, Rust command building |
| **Critical Security** | 5 | Block eval, os, subprocess, fs; allow safe code |
| **Job Service** | 5 | Create, get, mark processing/completed, exists |
| **Integration** | 5 | Filename validation, validator dispatch, lifecycle |
| **Auth** | 5 | Valid/invalid/missing keys, constant-time, exclusions |
| **Total** | **25** | **~75% of critical paths** |

### What's NOT Covered?

The minimal suite skips:
- Edge cases (covered by full suite)
- Exhaustive security bypass attempts
- Concurrent job handling
- Detailed error scenarios
- WebSocket connection edge cases

These are still covered by the full suite, which you run before deployment.

## Daily Workflow

### 🌅 Morning (Starting Work)

```bash
# Quick health check
pytest tests/test_minimal.py --tb=short
```

**Result:** 25 passed in ~15s
**Action:** Start coding with confidence

### 💻 During Development

```bash
# After each small change
pytest tests/test_minimal.py -k "executor or security"

# After adding a feature
pytest tests/test_minimal.py -v
```

**Result:** Fast feedback on critical paths
**Action:** Continue coding or fix failures

### 🎯 Before Commit

```bash
# Run minimal suite
pytest tests/test_minimal.py

# If all pass, commit
git add .
git commit -m "Add feature X"
```

**Result:** Confidence in core functionality
**Action:** Commit changes

### 🚀 Before Deployment

```bash
# Run FULL suite with coverage
pytest

# Check coverage report
open htmlcov/index.html
```

**Result:** Comprehensive validation
**Action:** Deploy if all pass

## When to Add Tests

### Add to Minimal Suite

Only add tests to the minimal suite if they meet **ALL** criteria:
1. ✅ Test breaks frequently when code changes
2. ✅ Failure indicates critical functionality is broken
3. ✅ Test runs in <1 second
4. ✅ Test is easy to understand and maintain

**Example:** If you find a critical bug in production, add a regression test to the minimal suite.

### Add to Full Suite

Add to the full suite if:
- Test is valuable but slow
- Test covers an edge case
- Test is for comprehensive coverage
- Test requires complex setup

## Maintenance Strategy

### Daily (5 minutes)
- Run minimal suite
- Fix failures immediately
- Don't skip failing tests

### Weekly (30 minutes)
- Review test failures
- Update tests if APIs changed
- Clean up outdated tests

### Monthly (2 hours)
- Run full suite
- Review coverage report
- Identify gaps
- Refactor brittle tests

### Before Major Release (4 hours)
- Run full suite multiple times
- Test edge cases manually
- Review security tests
- Load testing (if applicable)

## Red Flags 🚩

Stop and reconsider if you experience:

1. **Tests break on every code change**
   - Tests are too brittle
   - Solution: Mock external dependencies better

2. **Can't remember what a test does**
   - Test names unclear
   - Solution: Rename with descriptive names

3. **Dread writing new features because of test maintenance**
   - Too many tests
   - Solution: Remove redundant tests

4. **Minimal suite takes >30 seconds**
   - Too many tests in minimal suite
   - Solution: Move slow tests to full suite

5. **More test code than production code**
   - Over-testing
   - Solution: Focus on critical paths

## Comparison: Minimal vs Full Suite

| Metric | Minimal Suite | Full Suite |
|--------|--------------|-----------|
| **Tests** | 25 | 90+ |
| **Runtime** | ~15 seconds | ~30-60 seconds |
| **Coverage** | ~75% | ~88% |
| **Maintenance** | Low (1 file) | High (multiple files) |
| **Use Case** | Daily development | Before deployment |
| **Feedback Speed** | Instant | Moderate |
| **Confidence Level** | Core features work | Everything works |

## Tips for Solo Developers

### 1. Run Minimal Suite Always

```bash
# Add to your shell rc file
alias test-quick="cd backend && pytest tests/test_minimal.py --tb=short"
alias test-full="cd backend && pytest"

# Use in development
test-quick   # During development
test-full    # Before push/deploy
```

### 2. Don't Skip Tests

Even if you're in a hurry, run at least the minimal suite. 15 seconds is worth it to avoid breaking production.

### 3. Keep It Fast

If the minimal suite gets slow (>30s), remove tests or optimize them. Speed is critical for daily use.

### 4. Trust the Process

- **Morning:** Run minimal suite
- **During work:** Run relevant subset
- **Before commit:** Run minimal suite
- **Before deploy:** Run full suite

This rhythm keeps you productive without sacrificing quality.

### 5. Add Tests for Bugs

When you find a bug:
1. Write a test that reproduces it
2. Fix the bug
3. Verify test passes
4. Add to minimal suite if critical

This prevents regressions.

## Example Output

### Successful Run

```
$ pytest tests/test_minimal.py --tb=short

========================== test session starts ===========================
collected 25 items

tests/test_minimal.py::test_python_executor_command_building PASSED    [  4%]
tests/test_minimal.py::test_javascript_executor_command_building PASSED[  8%]
tests/test_minimal.py::test_c_executor_compilation PASSED              [ 12%]
tests/test_minimal.py::test_cpp_executor_compilation PASSED            [ 16%]
tests/test_minimal.py::test_rust_executor_compilation PASSED           [ 20%]
tests/test_minimal.py::test_python_blocks_eval PASSED                  [ 24%]
tests/test_minimal.py::test_python_blocks_os_module PASSED             [ 28%]
tests/test_minimal.py::test_python_blocks_subprocess PASSED            [ 32%]
tests/test_minimal.py::test_javascript_blocks_require_fs PASSED        [ 36%]
tests/test_minimal.py::test_python_allows_safe_code PASSED             [ 40%]
tests/test_minimal.py::test_job_service_create_job PASSED              [ 44%]
tests/test_minimal.py::test_job_service_get_job PASSED                 [ 48%]
tests/test_minimal.py::test_job_service_mark_processing PASSED         [ 52%]
tests/test_minimal.py::test_job_service_mark_completed PASSED          [ 56%]
tests/test_minimal.py::test_job_service_job_exists PASSED              [ 60%]
tests/test_minimal.py::test_executor_filename_validation PASSED        [ 64%]
tests/test_minimal.py::test_executor_filename_allows_valid PASSED      [ 68%]
tests/test_minimal.py::test_code_validator_dispatches_to_python PASSED [ 72%]
tests/test_minimal.py::test_code_validator_dispatches_to_javascript PASSED [ 76%]
tests/test_minimal.py::test_job_lifecycle_complete_flow PASSED         [ 80%]
tests/test_minimal.py::test_auth_verify_api_key_valid PASSED           [ 84%]
tests/test_minimal.py::test_auth_verify_api_key_invalid PASSED         [ 88%]
tests/test_minimal.py::test_auth_verify_api_key_missing PASSED         [ 92%]
tests/test_minimal.py::test_auth_uses_constant_time_comparison PASSED  [ 96%]
tests/test_minimal.py::test_auth_middleware_excludes_health_endpoint PASSED [100%]

========================== 25 passed in 14.28s ===========================
```

### Failed Run

```
$ pytest tests/test_minimal.py --tb=short

========================== test session starts ===========================
FAILED tests/test_minimal.py::test_python_blocks_eval - AssertionError

========================== FAILURES =======================================
tests/test_minimal.py::test_python_blocks_eval
    assert is_valid is False
    AssertionError: Security validation failed

========================== 1 failed, 24 passed in 14.45s ==================
```

**Action:** Fix the security validation before continuing development.

## Summary

The minimal test suite is your **daily driver** for development:

- ✅ Run it every morning
- ✅ Run it before every commit
- ✅ Run it during development for quick feedback
- ✅ Keep it fast (<30 seconds)
- ✅ Keep it simple (single file)

Save the full suite for before deployment and major releases.

**Remember:** 75% coverage with fast feedback is better than 90% coverage that you never run because it's too slow.

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│  MINIMAL TEST SUITE QUICK REFERENCE                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Run Command:                                            │
│  $ pytest tests/test_minimal.py --tb=short               │
│                                                          │
│  Tests: 25                                               │
│  Runtime: ~15 seconds                                    │
│  Coverage: ~75%                                          │
│                                                          │
│  Categories:                                             │
│  • 5 Executor smoke tests                                │
│  • 5 Security tests                                      │
│  • 5 Job service tests                                   │
│  • 5 Integration tests                                   │
│  • 5 Auth tests                                          │
│                                                          │
│  When to Run:                                            │
│  ✓ Every morning (health check)                          │
│  ✓ After each feature (sanity check)                     │
│  ✓ Before every commit (quality gate)                    │
│                                                          │
│  When to Run Full Suite:                                 │
│  ✓ Before deployment                                     │
│  ✓ Before major releases                                 │
│  ✓ Weekly/monthly comprehensive check                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```
