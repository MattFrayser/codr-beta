"""
Tests for Job Service

Covers:
- Job creation
- Job retrieval
- Job status updates
- Job lifecycle management
"""

import pytest
from api.services.job_service import JobService


class TestJobServiceOperations:
    """Test suite for job service CRUD operations"""

    @pytest.mark.asyncio
    async def test_creates_job_with_uuid(self, job_service):
        """Should create job with valid UUID"""
        job_id = await job_service.create_job(
            code="print('test')",
            language="python",
            filename="test.py"
        )

        assert job_id is not None
        assert len(job_id) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert "-" in job_id

    @pytest.mark.asyncio
    async def test_retrieves_job_metadata(self, job_service):
        """Should retrieve stored job metadata"""
        job_id = await job_service.create_job(
            code="print('hello')",
            language="python",
            filename="test.py"
        )

        job = await job_service.get_job(job_id)

        assert job is not None
        assert job.job_id == job_id
        assert job.code == "print('hello')"
        assert job.language == "python"
        assert job.filename == "test.py"
        assert job.status == "queued"

    @pytest.mark.asyncio
    async def test_marks_job_as_processing(self, job_service):
        """Should update job status to processing"""
        job_id = await job_service.create_job(
            code="print('test')",
            language="python",
            filename="test.py"
        )

        await job_service.mark_processing(job_id)

        job = await job_service.get_job(job_id)
        assert job.status == "processing"

    @pytest.mark.asyncio
    async def test_marks_job_as_completed(self, job_service):
        """Should update job status to completed with result"""
        job_id = await job_service.create_job(
            code="print('test')",
            language="python",
            filename="test.py"
        )

        result = {
            "success": True,
            "exit_code": 0,
            "stdout": "test\n",
            "stderr": "",
            "execution_time": 0.5
        }

        await job_service.mark_completed(job_id, result)

        job = await job_service.get_job(job_id)
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_checks_job_existence(self, job_service):
        """Should check if job exists in storage"""
        job_id = await job_service.create_job(
            code="print('test')",
            language="python",
            filename="test.py"
        )

        exists = await job_service.job_exists(job_id)
        assert exists is True

        fake_exists = await job_service.job_exists("fake-job-id-12345")
        assert fake_exists is False


class TestJobServiceLifecycle:
    """Test suite for complete job lifecycle"""

    @pytest.mark.asyncio
    async def test_complete_job_lifecycle(self, job_service):
        """Should handle complete job lifecycle from creation to completion"""
        # Create
        job_id = await job_service.create_job(
            code="print('lifecycle test')",
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
    async def test_handles_failed_jobs(self, job_service):
        """Should handle job failures appropriately"""
        job_id = await job_service.create_job(
            code="invalid code",
            language="python",
            filename="test.py"
        )

        error_message = "Compilation failed"
        result = {"success": False, "exit_code": 1, "stderr": error_message}

        await job_service.mark_failed(job_id, error_message, result)

        job = await job_service.get_job(job_id)
        assert job.status == "failed"
