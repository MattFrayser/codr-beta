"""JWT token management for job authentication."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from fastapi import HTTPException
from lib.config.settings import get_settings
from lib.redis import get_async_redis


class JobTokenManager:
    """Manages creation and validation of job-scoped JWT tokens."""

    def __init__(self):
        self.settings = get_settings()

    def create_job_token(self, job_id: str) -> Dict[str, str]:
        """
        Create a new job token.

        Args:
            job_id: Unique job identifier

        Returns:
            Dict with job_id, job_token, and expires_at
        """
        now = datetime.utcnow()
        expiration = now + timedelta(minutes=self.settings.jwt_expiration_minutes)

        # JWT payload (claims)
        payload = {
            "job_id": job_id,
            "iat": now,  # Issued at
            "exp": expiration,  # Expiration
            "jti": str(uuid.uuid4()),  # JWT ID (for single-use tracking)
        }

        # Sign the token
        token = jwt.encode(
            payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm
        )

        return {
            "job_id": job_id,
            "job_token": token,
            "expires_at": expiration.isoformat(),
        }

    def verify_job_token(self, token: str, expected_job_id: str) -> Dict:
        """
        Verify and decode a job token.

        Args:
            token: JWT token to verify
            expected_job_id: Expected job_id in token claims

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid, expired, or job_id mismatch
        """
        try:
            # Decode and verify signature + expiration
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
            )

            # Verify job_id matches
            if payload.get("job_id") != expected_job_id:
                raise HTTPException(status_code=403, detail="Token job_id mismatch")

            return payload

        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Job token has expired")
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid job token: {str(e)}")

    async def mark_token_used(self, jti: str) -> None:
        """
        Mark a token as used (single-use enforcement).

        Args:
            jti: JWT ID from token claims

        Note: Uses Redis to track used tokens. Token entry expires automatically.
        """
        try:
            redis = await get_async_redis()
            # Store token ID with TTL matching JWT expiration
            ttl = self.settings.jwt_expiration_minutes * 60
            await redis.setex(f"used_token:{jti}", ttl, "1")
        except Exception as e:
            # Log error but don't block execution if Redis is unavailable
            print(f"Warning: Failed to mark token as used: {e}")

    async def is_token_used(self, jti: str) -> bool:
        """
        Check if a token has already been used.

        Args:
            jti: JWT ID from token claims

        Returns:
            True if token was already used, False otherwise
        """
        try:
            redis = await get_async_redis()
            result = await redis.exists(f"used_token:{jti}")
            return bool(result)
        except Exception as e:
            # If Redis is unavailable, allow the request (fail open)
            # In production, you might want to fail closed instead
            print(f"Warning: Failed to check token usage: {e}")
            return False


# Singleton instance
_token_manager: Optional[JobTokenManager] = None


def get_token_manager() -> JobTokenManager:
    """Get the JobTokenManager singleton."""
    global _token_manager
    if _token_manager is None:
        _token_manager = JobTokenManager()
    return _token_manager
