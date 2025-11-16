"""
Tests for Rust Executor

Covers:
- Command building
- Compilation with rustc
- Compiler flags
- Filename validation
"""

import pytest
from executors.rust import RustExecutor


class TestRustExecutor:
    """Test suite for Rust code compilation and execution"""

    def test_builds_compiler_command(self, rust_executor, sample_rust_code, tmp_path):
        """Should compile Rust code and return binary path"""
        filepath = tmp_path / "test.rs"
        filepath.write_text(sample_rust_code)

        command = rust_executor._build_command(str(filepath), str(tmp_path))

        # Should return path to compiled binary
        assert len(command) == 1
        assert "program" in command[0]
        assert str(tmp_path) in command[0]

    def test_uses_rustc_compiler(self, rust_executor):
        """Should use rustc as the Rust compiler"""
        compiler, flags = rust_executor._get_compiler_config()

        assert compiler == "rustc"
        assert isinstance(flags, list)

    def test_validates_filename_format(self, rust_executor):
        """Should validate filename follows allowed format"""
        # Valid filenames should not raise
        rust_executor._validateFileName("test.rs")
        rust_executor._validateFileName("main.rs")
        rust_executor._validateFileName("lib.rs")

    def test_blocks_path_traversal(self, rust_executor):
        """Should block path traversal attempts in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            rust_executor._validateFileName("../../../etc/passwd")

    def test_blocks_absolute_paths(self, rust_executor):
        """Should block absolute paths in filename"""
        with pytest.raises(ValueError, match="Invalid filename"):
            rust_executor._validateFileName("/etc/passwd")
