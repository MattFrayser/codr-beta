"""
Tests for C++ Executor

Covers:
- Command building
- Compilation with g++
- Compiler flags
- Filename validation
"""

import pytest
from executors.cpp import CppExecutor


class TestCppExecutor:
    """Test suite for C++ code compilation and execution"""

    def test_builds_compiler_command(self, cpp_executor, sample_cpp_code, tmp_path):
        """Should compile C++ code and return binary path"""
        filepath = tmp_path / "test.cpp"
        filepath.write_text(sample_cpp_code)

        command = cpp_executor._build_command(str(filepath), str(tmp_path))

        # Should return path to compiled binary
        assert len(command) == 1
        assert "program" in command[0]
        assert str(tmp_path) in command[0]

    def test_uses_gpp_compiler(self, cpp_executor):
        """Should use g++ as the C++ compiler"""
        compiler, flags = cpp_executor._get_compiler_config()

        assert compiler == "g++"
        assert isinstance(flags, list)

    def test_uses_cpp17_standard(self, cpp_executor):
        """Should compile with C++17 standard"""
        compiler, flags = cpp_executor._get_compiler_config()

        assert "-std=c++17" in flags

    def test_validates_filename_format(self, cpp_executor):
        """Should validate filename follows allowed format"""
        # Valid filenames should not raise
        cpp_executor._validateFileName("test.cpp")
        cpp_executor._validateFileName("main.cpp")
        cpp_executor._validateFileName("program.cpp")

    def test_blocks_path_traversal(self, cpp_executor):
        """Should block path traversal attempts in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            cpp_executor._validateFileName("../../../etc/passwd")
