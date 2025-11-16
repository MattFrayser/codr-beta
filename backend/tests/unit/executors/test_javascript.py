"""
Tests for JavaScript Executor

Covers:
- Command building
- Filename validation
- Node.js execution setup
"""

import pytest
from executors.javascript import JavaScriptExecutor


class TestJavaScriptExecutor:
    """Test suite for JavaScript code execution"""

    def test_builds_correct_command(self, javascript_executor):
        """Should build correct node command with memory/GC flags"""
        command = javascript_executor._build_command("/tmp/test.js", "/tmp")

        assert command == [
            "node",
            "--max-old-space-size=64",
            "--no-concurrent-recompilation",
            "--single-threaded-gc",
            "/tmp/test.js"
        ]
        assert len(command) == 5

    def test_validates_filename_format(self, javascript_executor):
        """Should validate filename follows allowed format"""
        # Valid filenames should not raise
        javascript_executor._validateFileName("test.js")
        javascript_executor._validateFileName("main.js")
        javascript_executor._validateFileName("my_file.js")
        javascript_executor._validateFileName("index.js")

    def test_blocks_path_traversal(self, javascript_executor):
        """Should block path traversal attempts in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            javascript_executor._validateFileName("../../../etc/passwd")

    def test_blocks_absolute_paths(self, javascript_executor):
        """Should block absolute paths in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            javascript_executor._validateFileName("/etc/passwd")

    def test_blocks_special_characters(self, javascript_executor):
        """Should block special characters in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            javascript_executor._validateFileName("test;rm.js")
