"""
Tests for Security Validation

Covers:
- Python AST validation (blocking dangerous operations)
- JavaScript validation (blocking dangerous modules)
- Safe code validation
- Validator dispatch
"""

import pytest
from lib.security.validator import CodeValidator
from lib.security.python_ast_validator import PythonASTValidator


class TestPythonSecurityValidation:
    """Test suite for Python code security validation"""

    def test_blocks_eval_function(self, python_validator):
        """Should block eval() function"""
        malicious_code = """
eval("print('hacked')")
"""
        is_valid, error = python_validator.validate(malicious_code)

        assert is_valid is False
        assert "eval" in error.lower()

    def test_blocks_exec_function(self, python_validator):
        """Should block exec() function"""
        malicious_code = """
exec("import os")
"""
        is_valid, error = python_validator.validate(malicious_code)

        assert is_valid is False
        assert "exec" in error.lower()

    def test_blocks_os_module(self, python_validator):
        """Should block os module import"""
        malicious_code = """
import os
os.system("ls")
"""
        is_valid, error = python_validator.validate(malicious_code)

        assert is_valid is False
        assert "os" in error.lower()

    def test_blocks_subprocess_module(self, python_validator):
        """Should block subprocess module"""
        malicious_code = """
import subprocess
subprocess.run(["ls"])
"""
        is_valid, error = python_validator.validate(malicious_code)

        assert is_valid is False
        assert "subprocess" in error.lower()

    def test_allows_safe_code(self, python_validator):
        """Should allow safe Python code"""
        safe_code = """
def add(a, b):
    return a + b

result = add(2, 3)
print(result)
"""
        is_valid, error = python_validator.validate(safe_code)

        assert is_valid is True
        assert error == ""

    def test_allows_safe_imports(self, python_validator):
        """Should allow safe module imports"""
        safe_code = """
import math
import random

result = math.sqrt(16)
print(result)
"""
        is_valid, error = python_validator.validate(safe_code)

        assert is_valid is True
        assert error == ""


class TestJavaScriptSecurityValidation:
    """Test suite for JavaScript code security validation"""

    def test_blocks_require_fs(self, code_validator):
        """Should block require('fs') in JavaScript"""
        malicious_code = """
const fs = require('fs');
fs.readFileSync('/etc/passwd');
"""
        is_valid, error = code_validator.validate(malicious_code, "javascript")

        assert is_valid is False
        assert "fs" in error.lower() or "require" in error.lower()

    def test_blocks_require_child_process(self, code_validator):
        """Should block require('child_process')"""
        malicious_code = """
const { exec } = require('child_process');
exec('ls');
"""
        is_valid, error = code_validator.validate(malicious_code, "javascript")

        assert is_valid is False

    def test_allows_safe_javascript(self, code_validator):
        """Should allow safe JavaScript code"""
        safe_code = """
function add(a, b) {
    return a + b;
}

const result = add(2, 3);
console.log(result);
"""
        is_valid, error = code_validator.validate(safe_code, "javascript")

        assert is_valid is True
        assert error == ""


class TestCodeValidatorDispatch:
    """Test suite for CodeValidator dispatching to language-specific validators"""

    def test_dispatches_to_python_validator(self, code_validator):
        """Should dispatch Python code to Python validator"""
        code = "import os"

        is_valid, error = code_validator.validate(code, "python")

        assert is_valid is False
        assert "os" in error.lower()

    def test_dispatches_to_javascript_validator(self, code_validator):
        """Should dispatch JavaScript code to JavaScript validator"""
        code = "const fs = require('fs');"

        is_valid, error = code_validator.validate(code, "javascript")

        assert is_valid is False
