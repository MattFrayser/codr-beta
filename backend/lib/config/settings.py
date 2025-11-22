"""
Application Configuration Management
Uses Pydantic Settings for type-safe configuration with automatic
environment variable loading and validation.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Optional


class AppSettings(BaseSettings):
    """Application settings - all configuration in one place"""

    # Server Configuration
    env: str = Field(default="production", description="Environment mode")
    api_key: Optional[str] = Field(default=None, description="API authentication key")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    cors_origins: str = Field(default="*", description="CORS origins (comma-separated)")

    # JWT Configuration
    jwt_secret: str = Field(..., description="Secret key for JWT signing")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expiration_minutes: int = Field(
        default=15, description="JWT token expiration in minutes"
    )

    # Execution Configuration
    execution_timeout: int = Field(
        default=7, description="Execution timeout in seconds"
    )
    max_memory_mb: int = Field(
        default=300, description="Maximum memory per execution in MB"
    )
    max_file_size_mb: int = Field(
        default=1, description="Maximum output file size in MB"
    )
    compilation_timeout: int = Field(
        default=10, description="Compilation timeout in seconds"
    )
    max_input_kb: int = Field(default=100, description="Maximum input size in KB")

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_ttl: int = Field(default=3600, description="Job TTL in seconds")

    # Polling Configuration
    max_poll_attempts: int = Field(default=60, description="Maximum polling attempts")
    poll_interval: int = Field(default=1, description="Poll interval in seconds")

    # Rate Limiting Configuration
    rate_limit_submit: str = Field(
        default="10/minute", description="Submit endpoint rate limit"
    )
    rate_limit_stream: str = Field(
        default="30/minute", description="Stream endpoint rate limit"
    )

    # Job Queue Configuration
    job_queue_name: str = Field(
        default="codr:job_queue", description="Redis job queue name"
    )
    worker_poll_timeout: int = Field(
        default=5, description="Worker queue poll timeout in seconds"
    )
    worker_id: Optional[str] = Field(
        default=None, description="Worker identifier (auto-generated if not set)"
    )
    max_queue_size: int = Field(default=1000, description="Maximum job queue size")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> AppSettings:
    """
    Get cached settings instance

    This function is cached to ensure settings are loaded only once
    and reused throughout the application lifecycle.

    """
    return AppSettings()  # type: ignore[call-arg]
