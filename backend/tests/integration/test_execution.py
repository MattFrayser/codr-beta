"""
Integration Tests for Code Execution

Covers:
- End-to-end execution flow
- Validator integration
- Executor integration
- Job service integration
"""

import pytest
from api.security.validator import CodeValidator
from executors import get_executor


class TestExecutorIntegration:
    """Test suite for executor integration with validation"""

    def test_filename_validation_in_executor(self, python_executor):
        """Should validate filename format in executor"""
        with pytest.raises(ValueError, match="Invalid filename"):
            python_executor._validateFileName("../../../etc/passwd")

    def test_executor_allows_valid_filenames(self, python_executor):
        """Should allow valid filenames through executor validation"""
        # Should not raise
        python_executor._validateFileName("test.py")
        python_executor._validateFileName("main.py")
        python_executor._validateFileName("my_file.py")


class TestValidatorIntegration:
    """Test suite for validator integration with different languages"""

    def test_validator_dispatches_to_python(self, code_validator):
        """Should dispatch Python code to Python validator"""
        code = "import os"

        is_valid, error = code_validator.validate(code, "python")

        assert is_valid is False
        assert "os" in error.lower()

    def test_validator_dispatches_to_javascript(self, code_validator):
        """Should dispatch JavaScript code to JavaScript validator"""
        code = """
const fs = require('fs');
"""
        is_valid, error = code_validator.validate(code, "javascript")

        assert is_valid is False

    def test_validator_handles_safe_code(self, code_validator):
        """Should allow safe code through validation"""
        safe_python = """
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
"""
        is_valid, error = code_validator.validate(safe_python, "python")

        assert is_valid is True
        assert error == ""


class TestExecutorFactory:
    """Test suite for executor factory pattern"""

    def test_gets_python_executor(self):
        """Should return Python executor for 'python' language"""
        from executors.python import PythonExecutor

        executor = get_executor("python")

        assert isinstance(executor, PythonExecutor)

    def test_gets_javascript_executor(self):
        """Should return JavaScript executor for 'javascript' language"""
        from executors.javascript import JavaScriptExecutor

        executor = get_executor("javascript")

        assert isinstance(executor, JavaScriptExecutor)

    def test_gets_c_executor(self):
        """Should return C executor for 'c' language"""
        from executors.c import CExecutor

        executor = get_executor("c")

        assert isinstance(executor, CExecutor)

    def test_raises_for_unsupported_language(self):
        """Should raise ValueError for unsupported language"""
        with pytest.raises(ValueError, match="Unsupported language"):
            get_executor("fortran")


class TestJobServiceIntegration:
    """Test suite for job service integration with complete flow"""

    @pytest.mark.asyncio
    async def test_job_lifecycle_complete_flow(self, job_service):
        """Should handle complete job lifecycle from creation to completion"""
        # Create
        job_id = await job_service.create_job(
            code="print('integration test')",
            language="python",
            filename="test.py"
        )
        job = await job_service.get_job(job_id)
        assert job.status == "queued"

        # Process
        await job_service.mark_processing(job_id)
        job = await job_service.get_job(job_id)
        assert job.status == "processing"

        # Complete
        result = {"success": True, "exit_code": 0}
        await job_service.mark_completed(job_id, result)
        job = await job_service.get_job(job_id)
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_job_creation_with_all_languages(self, job_service):
        """Should create jobs for all supported languages"""
        languages = ["python", "javascript", "c", "cpp", "rust"]

        for language in languages:
            job_id = await job_service.create_job(
                code="// test code",
                language=language,
                filename=f"test.{language}"
            )

            assert job_id is not None
            job = await job_service.get_job(job_id)
            assert job.language == language
