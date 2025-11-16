"""
Tests for C Executor

Covers:
- Command building
- Compilation with gcc
- Compiler flags
- Filename validation
"""

import pytest
from executors.c import CExecutor


class TestCExecutor:
    """Test suite for C code compilation and execution"""

    def test_builds_compiler_command(self, c_executor, sample_c_code, tmp_path):
        """Should compile C code and return binary path"""
        filepath = tmp_path / "test.c"
        filepath.write_text(sample_c_code)

        command = c_executor._build_command(str(filepath), str(tmp_path))

        # Should return path to compiled binary
        assert len(command) == 1
        assert "program" in command[0]
        assert str(tmp_path) in command[0]

    def test_uses_gcc_compiler(self, c_executor):
        """Should use gcc as the C compiler"""
        compiler, flags = c_executor._get_compiler_config()

        assert compiler == "gcc"
        assert isinstance(flags, list)

    def test_uses_c11_standard(self, c_executor):
        """Should compile with C11 standard"""
        compiler, flags = c_executor._get_compiler_config()

        assert "-std=c11" in flags

    def test_includes_math_library(self, c_executor):
        """Should include math library flag"""
        compiler, flags = c_executor._get_compiler_config()

        assert "-lm" in flags

    def test_validates_filename_format(self, c_executor):
        """Should validate filename follows allowed format"""
        # Valid filenames should not raise
        c_executor._validateFileName("test.c")
        c_executor._validateFileName("main.c")
        c_executor._validateFileName("program.c")
