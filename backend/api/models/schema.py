from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional

from executors import get_supported_languages


class CodeSubmission(BaseModel):

    code: str = Field(..., min_length=1, max_length=10240, description="Code to execute (max 10KB)")
    language: str = Field(..., description="Programming language")
    filename: str = Field(..., description="File name with extension")

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        supported = get_supported_languages()
        if v.lower() not in supported:
            supported_list = ', '.join(sorted(supported))
            raise ValueError(f"Language must be one of: {supported_list}")
        return v.lower()

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError("Filename can only contain alphanumeric characters, dots, hyphens, and underscores")
        if '..' in v or v.startswith('/'):
            raise ValueError("Invalid filename: path traversal detected")
        if len(v) > 255:
            raise ValueError("Filename too long (max 255 characters)")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "print('Hello, World!')",
                "language": "python",
                "filename": "hello.py"
            }
        }
    )


class JobResponse(BaseModel):
    """Model for job submission response"""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    message: Optional[str] = Field(None, description="Additional message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "abc123",
                "status": "queued",
                "message": "Job submitted successfully"
            }
        }
    )


class JobResult(BaseModel):
    """Model for job execution result"""

    job_id: str
    status: str  # queued, processing, completed, failed, unknown
    code: Optional[str] = None
    language: Optional[str] = None
    filename: Optional[str] = None
    result: Optional[dict] = None  # {success, stdout, stderr, exit_code, execution_time}
    error: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "abc123",
                "status": "completed",
                "language": "python",
                "filename": "hello.py",
                "result": {
                    "success": True,
                    "stdout": "Hello, World!\n",
                    "stderr": "",
                    "exit_code": 0,
                    "execution_time": 0.123
                }
            }
        }
    )
