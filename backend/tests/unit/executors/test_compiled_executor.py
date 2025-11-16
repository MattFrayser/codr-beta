"""
Unit tests for CompiledExecutor base class

Tests the compiled language executor for:
- Compilation process
- Compiler configuration
- Compilation timeout
- Compilation error handling
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock
from executors.c import CExecutor
from executors.cpp import CppExecutor
from executors.rust import RustExecutor


@pytest.mark.unit
class TestCExecutor:
    """Test suite for C executor"""

    def test_compiler_config(self, c_executor):
        """Test C compiler configuration"""
        compiler, flags = c_executor._get_compiler_config()

        assert compiler == 'gcc'
        assert '-std=c11' in flags
        assert '-lm' in flags  # Math library

    def test_build_command_creates_binary(self, c_executor, tmp_path):
        """Test that build_command compiles C code"""
        source_file = tmp_path / "test.c"
        source_file.write_text("""
#include <stdio.h>
int main() {
    printf("Hello\\n");
    return 0;
}
""")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr='')

            command = c_executor._build_command(str(source_file), str(tmp_path))

            # Should return path to compiled binary
            assert len(command) == 1
            assert command[0].endswith('/program')

            # Verify compilation was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert 'gcc' in call_args
            assert '-o' in call_args

    def test_compilation_failure(self, c_executor, tmp_path):
        """Test handling of compilation errors"""
        source_file = tmp_path / "test.c"
        source_file.write_text("""
#include <stdio.h>
int main() {
    invalid_function();  // Compilation error
    return 0;
}
""")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stderr="error: implicit declaration of function 'invalid_function'"
            )

            with pytest.raises(Exception, match="Compilation failed"):
                c_executor._build_command(str(source_file), str(tmp_path))

    def test_compilation_timeout(self, c_executor, tmp_path):
        """Test compilation timeout handling"""
        source_file = tmp_path / "test.c"
        source_file.write_text("#include <stdio.h>\nint main() { return 0; }")

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('gcc', 10)

            with pytest.raises(Exception, match="Compilation timed out"):
                c_executor._build_command(str(source_file), str(tmp_path))


@pytest.mark.unit
class TestCppExecutor:
    """Test suite for C++ executor"""

    def test_compiler_config(self, cpp_executor):
        """Test C++ compiler configuration"""
        compiler, flags = cpp_executor._get_compiler_config()

        assert compiler == 'g++'
        assert '-std=c++17' in flags
        assert '-lstdc++' in flags  # C++ standard library

    def test_build_command_compiles_cpp(self, cpp_executor, tmp_path):
        """Test C++ code compilation"""
        source_file = tmp_path / "test.cpp"
        source_file.write_text("""
#include <iostream>
int main() {
    std::cout << "Hello" << std::endl;
    return 0;
}
""")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr='')

            command = cpp_executor._build_command(str(source_file), str(tmp_path))

            assert len(command) == 1
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert 'g++' in call_args


@pytest.mark.unit
class TestRustExecutor:
    """Test suite for Rust executor"""

    def test_compiler_config(self, rust_executor):
        """Test Rust compiler configuration"""
        compiler, flags = rust_executor._get_compiler_config()

        assert compiler == 'rustc'
        assert flags == []  # No additional flags needed

    def test_build_command_compiles_rust(self, rust_executor, tmp_path):
        """Test Rust code compilation"""
        source_file = tmp_path / "test.rs"
        source_file.write_text("""
fn main() {
    println!("Hello");
}
""")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr='')

            command = rust_executor._build_command(str(source_file), str(tmp_path))

            assert len(command) == 1
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert 'rustc' in call_args


@pytest.mark.unit
class TestCompiledExecutorShared:
    """Test shared compiled executor functionality"""

    @pytest.mark.parametrize("executor_fixture", [
        "c_executor",
        "cpp_executor",
        "rust_executor"
    ])
    def test_all_compiled_executors_have_config(self, executor_fixture, request):
        """Test all compiled executors implement compiler config"""
        executor = request.getfixturevalue(executor_fixture)

        compiler, flags = executor._get_compiler_config()

        assert compiler is not None
        assert isinstance(compiler, str)
        assert isinstance(flags, list)

    @pytest.mark.parametrize("executor_fixture", [
        "c_executor",
        "cpp_executor",
        "rust_executor"
    ])
    def test_all_compiled_executors_return_binary_path(self, executor_fixture, request, tmp_path):
        """Test all compiled executors return binary path"""
        executor = request.getfixturevalue(executor_fixture)
        source_file = tmp_path / "test.txt"
        source_file.write_text("// test")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr='')

            command = executor._build_command(str(source_file), str(tmp_path))

            assert len(command) == 1
            assert command[0].endswith('/program')
