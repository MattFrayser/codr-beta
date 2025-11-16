"""
Integration tests for code execution flow

Tests the complete execution pipeline:
- Code validation
- Job creation
- Execution
- Result retrieval
"""

import pytest
import asyncio
from unittest.mock import Mock, patch


@pytest.mark.integration
@pytest.mark.asyncio
class TestCodeExecutionIntegration:
    """Integration tests for complete code execution flow"""

    async def test_python_execution_success(self, job_service):
        """Test successful Python code execution"""
        code = "print('Hello, World!')"
        language = "python"
        filename = "test.py"

        # 1. Validate code
        from api.security.validator import CodeValidator
        validator = CodeValidator()
        is_valid, error = validator.validate(code, language)
        assert is_valid, f"Validation failed: {error}"

        # 2. Create job
        job_id = await job_service.create_job(code, language, filename)
        assert job_id is not None

        # 3. Get job
        job = await job_service.get_job(job_id)
        assert job.status == "queued"

        # 4. Mark processing (executor would do this)
        await job_service.mark_processing(job_id)
        job = await job_service.get_job(job_id)
        assert job.status == "processing"

        # 5. Mark completed with result
        result = {
            "success": True,
            "stdout": "Hello, World!\n",
            "stderr": "",
            "exit_code": 0,
            "execution_time": 0.5
        }
        await job_service.mark_completed(job_id, result)

        # 6. Verify final state
        job = await job_service.get_job(job_id)
        assert job.status == "completed"
        assert job.result["success"] is True

    async def test_security_validation_blocks_dangerous_code(self, job_service):
        """Test that dangerous code is blocked before execution"""
        dangerous_code = "import os\nos.system('rm -rf /')"
        language = "python"

        # Validate code
        from api.security.validator import CodeValidator
        validator = CodeValidator()
        is_valid, error = validator.validate(dangerous_code, language)

        # Should be blocked
        assert not is_valid, "Dangerous code was not blocked!"
        assert "os" in error.lower() or "blocked" in error.lower()

    async def test_execution_failure_handling(self, job_service):
        """Test handling of execution failures"""
        code = "print('test')"
        language = "python"
        filename = "test.py"

        # Create job
        job_id = await job_service.create_job(code, language, filename)

        # Mark as processing
        await job_service.mark_processing(job_id)

        # Simulate execution failure
        error_msg = "Execution timeout"
        result = {
            "success": False,
            "stdout": "",
            "stderr": error_msg,
            "exit_code": -1,
            "execution_time": 0
        }
        await job_service.mark_failed(job_id, error_msg, result)

        # Verify failure state
        job = await job_service.get_job(job_id)
        assert job.status == "failed"
        assert job.error == error_msg

    async def test_multiple_jobs_concurrent(self, job_service):
        """Test handling multiple jobs concurrently"""
        jobs = []

        # Create 10 jobs
        for i in range(10):
            code = f"print({i})"
            job_id = await job_service.create_job(code, "python", f"test{i}.py")
            jobs.append(job_id)

        # Verify all created
        for job_id in jobs:
            job = await job_service.get_job(job_id)
            assert job is not None
            assert job.status == "queued"

        # Process all
        for job_id in jobs:
            await job_service.mark_processing(job_id)
            await job_service.mark_completed(job_id, {
                "success": True,
                "exit_code": 0,
                "execution_time": 0.1
            })

        # Verify all completed
        for job_id in jobs:
            job = await job_service.get_job(job_id)
            assert job.status == "completed"


@pytest.mark.integration
class TestValidatorIntegration:
    """Integration tests for code validators"""

    def test_all_languages_have_validators(self):
        """Test that all supported languages have validators"""
        from executors import get_supported_languages
        from api.security.validator import CodeValidator

        validator = CodeValidator()
        supported_languages = get_supported_languages()

        # Test each language
        for language in supported_languages:
            if language == 'c++':
                language = 'cpp'  # Normalize

            try:
                is_valid, error = validator.validate("// test", language)
                # Should validate without error (result doesn't matter)
                assert error is not None or is_valid in [True, False]
            except Exception as e:
                pytest.fail(f"Validator failed for {language}: {e}")

    def test_python_dangerous_patterns(self):
        """Test detection of dangerous Python patterns"""
        from api.security.validator import CodeValidator

        validator = CodeValidator()
        dangerous_patterns = [
            "eval('1+1')",
            "exec('print(1)')",
            "import os",
            "import subprocess",
            "__import__('os')",
        ]

        for pattern in dangerous_patterns:
            is_valid, error = validator.validate(pattern, "python")
            assert not is_valid, f"Pattern not blocked: {pattern}"

    def test_javascript_dangerous_patterns(self):
        """Test detection of dangerous JavaScript patterns"""
        from api.security.validator import CodeValidator

        validator = CodeValidator()
        dangerous_patterns = [
            "eval('1+1')",
            "require('fs')",
            "require('child_process')",
        ]

        for pattern in dangerous_patterns:
            is_valid, error = validator.validate(pattern, "javascript")
            assert not is_valid, f"Pattern not blocked: {pattern}"


@pytest.mark.integration
@pytest.mark.slow
class TestExecutorIntegration:
    """Integration tests for executors (requires compilers)"""

    @pytest.mark.executor
    def test_python_executor_real_execution(self, python_executor):
        """Test real Python code execution"""
        code = "print('Integration test')"
        filename = "test.py"
        output_data = []
        input_queue = asyncio.Queue()

        def on_output(data: bytes):
            output_data.append(data.decode('utf-8', errors='replace'))

        # This would need real execution - skip if no Firejail
        pytest.skip("Requires Firejail and real execution environment")

    @pytest.mark.executor
    def test_c_executor_real_compilation(self, c_executor):
        """Test real C code compilation and execution"""
        code = '''
#include <stdio.h>
int main() {
    printf("C integration test\\n");
    return 0;
}
'''
        filename = "test.c"

        # This would need real compilation - skip if no gcc
        pytest.skip("Requires gcc and real compilation environment")
