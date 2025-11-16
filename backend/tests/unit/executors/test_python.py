"""
Tests for Python Executor
 
Covers:
- Command building
- Filename validation
- Compilation (N/A for Python, but includes structure for consistency)
"""
 
import pytest
from executors.python import PythonExecutor
 
 
class TestPythonExecutor:
 
    def test_builds_correct_command(self, python_executor):
        command = python_executor._build_command("/tmp/test.py", "/tmp")
 
        assert command == ["python3", "/tmp/test.py"]
        assert len(command) == 2
 
    def test_validates_filename_format(self, python_executor):
        # Valid filenames should not raise
        python_executor._validateFileName("test.py")
        python_executor._validateFileName("main.py")
        python_executor._validateFileName("my_file.py")
        python_executor._validateFileName("test123.py")
 
    def test_blocks_path_traversal(self, python_executor):
        """Should block path traversal attempts in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            python_executor._validateFileName("../../../etc/passwd")
 
        with pytest.raises(ValueError, match="Invalid filename"):
            python_executor._validateFileName("../../hack.py")
 
    def test_blocks_absolute_paths(self, python_executor):
        """Should block absolute paths in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            python_executor._validateFileName("/etc/passwd")
 
        with pytest.raises(ValueError, match="Invalid filename"):
            python_executor._validateFileName("/tmp/hack.py")
 
    def test_blocks_special_characters(self, python_executor):
        """Should block special characters in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            python_executor._validateFileName("test;rm -rf.py")
 
        with pytest.raises(ValueError, match="Invalid filename"):
            python_executor._validateFileName("test|hack.py")
