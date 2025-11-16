"""
Unit tests for PythonExecutor

Tests the Python code executor for:
- Successful execution
- Error handling
- Timeout behavior
- Resource limits
- Filename validation
"""

import pytest
import queue
from unittest.mock import Mock, patch, MagicMock
from executors.python import PythonExecutor


@pytest.mark.unit
class TestPythonExecutor:
    """Test suite for PythonExecutor"""

    def test_build_command(self, python_executor):
        """Test command building for Python execution"""
        command = python_executor._build_command("/tmp/test.py", "/tmp")

        assert command == ['python3', '/tmp/test.py']
        assert isinstance(command, list)

    def test_validate_filename_success(self, python_executor):
        """Test valid filename validation"""
        valid_filenames = [
            "test.py",
            "hello_world.py",
            "test-file.py",
            "test123.py",
        ]

        for filename in valid_filenames:
            # Should not raise exception
            python_executor._validateFileName(filename)

    def test_validate_filename_invalid_characters(self, python_executor):
        """Test invalid filename rejection"""
        invalid_filenames = [
            "test;.py",  # Semicolon
            "test$.py",  # Dollar sign
            "test&.py",  # Ampersand
            "test|.py",  # Pipe
        ]

        for filename in invalid_filenames:
            with pytest.raises(ValueError, match="Invalid filename"):
                python_executor._validateFileName(filename)

    def test_validate_filename_path_traversal(self, python_executor):
        """Test path traversal prevention"""
        traversal_attempts = [
            "../etc/passwd",
            "../../etc/passwd",
            "/etc/passwd",
            "test/../../../etc/passwd",
        ]

        for filename in traversal_attempts:
            with pytest.raises(ValueError, match="Invalid filename"):
                python_executor._validateFileName(filename)

    def test_write_to_file(self, python_executor, tmp_path):
        """Test writing code to temporary file"""
        code = "print('Hello, World!')"
        filename = "test.py"

        filepath = python_executor._writeToFile(str(tmp_path), code, filename)

        # Check file was created
        assert filepath == str(tmp_path / filename)

        # Check content
        with open(filepath, 'r') as f:
            content = f.read()

        assert content == code

    def test_build_sandbox_command(self, python_executor):
        """Test Firejail sandbox command construction"""
        command = ['python3', 'test.py']
        workdir = '/tmp/test'

        sandbox_cmd = python_executor._build_sandbox_command(command, workdir)

        # Verify Firejail is used
        assert sandbox_cmd[0] == '/usr/bin/firejail'

        # Verify security flags
        assert f'--private={workdir}' in sandbox_cmd
        assert '--net=none' in sandbox_cmd
        assert '--nodbus' in sandbox_cmd
        assert '--noroot' in sandbox_cmd

        # Verify resource limits
        assert any('--rlimit-as=' in arg for arg in sandbox_cmd)
        assert any('--rlimit-cpu=' in arg for arg in sandbox_cmd)
        assert any('--rlimit-fsize=' in arg for arg in sandbox_cmd)
        assert any('--timeout=' in arg for arg in sandbox_cmd)

        # Verify original command is appended
        assert 'python3' in sandbox_cmd
        assert 'test.py' in sandbox_cmd

    def test_executor_initialization(self, python_executor, test_settings):
        """Test executor initializes with correct settings"""
        assert python_executor.timeout == test_settings.execution_timeout
        assert python_executor.maxMemory == test_settings.max_memory_mb
        assert python_executor.maxFileSize == test_settings.max_file_size_mb


@pytest.mark.unit
@pytest.mark.slow
class TestPythonExecutorExecution:
    """Test suite for actual code execution (slower tests)"""

    def test_execute_simple_code_mock(self, python_executor):
        """Test execution with mocked PTY"""
        code = "print('Hello, World!')"
        filename = "test.py"
        output_data = []
        input_queue = queue.Queue()

        def on_output(data: bytes):
            output_data.append(data)

        with patch('os.read') as mock_read, \
             patch('os.write') as mock_write, \
             patch('os.close'), \
             patch('fcntl.ioctl'), \
             patch('fcntl.fcntl'), \
             patch('pty.openpty', return_value=(10, 11)), \
             patch('select.select', return_value=([10], [], [])), \
             patch('subprocess.Popen') as mock_popen:

            # Mock process
            mock_process = Mock()
            mock_process.poll.side_effect = [None, 0]  # Running, then finished
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            # Mock output
            mock_read.side_effect = [b"Hello, World!\n", b""]

            # Execute
            result = python_executor.execute(code, filename, on_output, input_queue)

            # Verify result structure
            assert "success" in result
            assert "exit_code" in result
            assert "execution_time" in result

    def test_format_error_result(self, python_executor):
        """Test error result formatting"""
        error = Exception("Test error")
        execution_time = 1.5

        result = python_executor._format_error_result(error, execution_time)

        assert result["success"] is False
        assert result["exit_code"] == -1
        assert result["execution_time"] == 1.5
        assert "Test error" in result["stderr"]


@pytest.mark.unit
class TestPythonExecutorEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_code(self, python_executor, tmp_path):
        """Test handling of empty code"""
        code = ""
        filename = "test.py"

        # Should write file successfully even with empty code
        filepath = python_executor._writeToFile(str(tmp_path), code, filename)

        with open(filepath, 'r') as f:
            content = f.read()

        assert content == ""

    def test_unicode_code(self, python_executor, tmp_path):
        """Test handling of Unicode characters"""
        code = "print('你好世界')  # Chinese: Hello World"
        filename = "test.py"

        filepath = python_executor._writeToFile(str(tmp_path), code, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert content == code

    def test_very_long_code(self, python_executor, tmp_path):
        """Test handling of very long code"""
        code = "print('x')\n" * 1000  # 1000 print statements
        filename = "test.py"

        filepath = python_executor._writeToFile(str(tmp_path), code, filename)

        with open(filepath, 'r') as f:
            content = f.read()

        assert len(content.split('\n')) == 1001  # 1000 lines + empty line
