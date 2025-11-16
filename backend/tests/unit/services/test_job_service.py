"""
Unit tests for JobService

Tests job lifecycle management:
- Job creation
- Job retrieval
- Status updates
- Job existence checks
"""

import pytest
import json
from api.services.job_service import JobService


@pytest.mark.unit
@pytest.mark.asyncio
class TestJobService:
    """Test suite for JobService"""

    async def test_create_job(self, job_service):
        """Test job creation"""
        code = "print('Hello')"
        language = "python"
        filename = "test.py"

        job_id = await job_service.create_job(code, language, filename)

        # Verify job ID is UUID format
        assert isinstance(job_id, str)
        assert len(job_id) == 36  # UUID length with dashes

        # Verify job exists
        exists = await job_service.job_exists(job_id)
        assert exists is True

    async def test_get_job(self, job_service):
        """Test job retrieval"""
        code = "print('Hello')"
        language = "python"
        filename = "test.py"

        # Create job
        job_id = await job_service.create_job(code, language, filename)

        # Retrieve job
        job = await job_service.get_job(job_id)

        assert job is not None
        assert job.job_id == job_id
        assert job.code == code
        assert job.language == language
        assert job.filename == filename
        assert job.status == "queued"
        assert job.created_at is not None

    async def test_get_nonexistent_job(self, job_service):
        """Test retrieving non-existent job"""
        job = await job_service.get_job("nonexistent-uuid")
        assert job is None

    async def test_mark_processing(self, job_service):
        """Test marking job as processing"""
        job_id = await job_service.create_job("print('x')", "python", "test.py")

        await job_service.mark_processing(job_id)

        job = await job_service.get_job(job_id)
        assert job.status == "processing"

    async def test_mark_completed(self, job_service):
        """Test marking job as completed"""
        job_id = await job_service.create_job("print('x')", "python", "test.py")

        result = {
            "success": True,
            "stdout": "x\n",
            "stderr": "",
            "exit_code": 0,
            "execution_time": 1.23
        }

        await job_service.mark_completed(job_id, result)

        job = await job_service.get_job(job_id)
        assert job.status == "completed"
        assert job.result == result
        assert job.completed_at is not None

    async def test_mark_failed(self, job_service):
        """Test marking job as failed"""
        job_id = await job_service.create_job("print('x')", "python", "test.py")

        error_msg = "Execution timeout"
        result = {
            "success": False,
            "stdout": "",
            "stderr": error_msg,
            "exit_code": -1,
            "execution_time": 0
        }

        await job_service.mark_failed(job_id, error_msg, result)

        job = await job_service.get_job(job_id)
        assert job.status == "failed"
        assert job.error == error_msg
        assert job.result == result

    async def test_get_job_status(self, job_service):
        """Test getting job status"""
        job_id = await job_service.create_job("print('x')", "python", "test.py")

        status = await job_service.get_job_status(job_id)
        assert status == "queued"

        await job_service.mark_processing(job_id)
        status = await job_service.get_job_status(job_id)
        assert status == "processing"

    async def test_get_status_nonexistent_job(self, job_service):
        """Test getting status of non-existent job"""
        status = await job_service.get_job_status("nonexistent-uuid")
        assert status is None

    async def test_job_exists_false(self, job_service):
        """Test job_exists returns False for non-existent job"""
        exists = await job_service.job_exists("nonexistent-uuid")
        assert exists is False

    async def test_job_key_format(self, job_service):
        """Test Redis key format"""
        key = job_service._job_key("test-123")
        assert key == "job:test-123"

    async def test_multiple_jobs(self, job_service):
        """Test creating and managing multiple jobs"""
        job_ids = []

        for i in range(5):
            job_id = await job_service.create_job(
                f"print({i})",
                "python",
                f"test{i}.py"
            )
            job_ids.append(job_id)

        # Verify all jobs exist
        for job_id in job_ids:
            exists = await job_service.job_exists(job_id)
            assert exists is True

        # Verify jobs have unique IDs
        assert len(job_ids) == len(set(job_ids))

    async def test_job_result_serialization(self, job_service):
        """Test that complex results are properly serialized"""
        job_id = await job_service.create_job("print('x')", "python", "test.py")

        complex_result = {
            "success": True,
            "stdout": "output\nwith\nmultiple\nlines",
            "stderr": "",
            "exit_code": 0,
            "execution_time": 1.5,
            "metadata": {
                "nested": "data",
                "list": [1, 2, 3]
            }
        }

        await job_service.mark_completed(job_id, complex_result)

        job = await job_service.get_job(job_id)
        assert job.result == complex_result

    async def test_lifecycle_progression(self, job_service):
        """Test complete job lifecycle"""
        # 1. Create
        job_id = await job_service.create_job("print('test')", "python", "test.py")
        job = await job_service.get_job(job_id)
        assert job.status == "queued"

        # 2. Start processing
        await job_service.mark_processing(job_id)
        job = await job_service.get_job(job_id)
        assert job.status == "processing"

        # 3. Complete
        result = {"success": True, "exit_code": 0, "execution_time": 1.0}
        await job_service.mark_completed(job_id, result)
        job = await job_service.get_job(job_id)
        assert job.status == "completed"
        assert job.result == result
