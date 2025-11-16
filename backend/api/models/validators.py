"""Validation utilities for models"""
import re


def validateFileName(filename: str) -> None:
    if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
        raise ValueError("Filename can only contain alphanumeric characters, dots, hyphens, and underscores")
    if '..' in filename or filename.startswith('/'):
        raise ValueError("Invalid filename: path traversal detected")
    if len(filename) > 255:
        raise ValueError("Filename too long (max 255 characters)")
