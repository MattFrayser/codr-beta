"""
Unit tests for Python AST Validator

Tests the Python code security validator for:
- Blocked operations detection
- Blocked modules detection
- Dunder attribute access
- Safe code validation
"""

import pytest
from api.security.python_ast_validator import PythonASTValidator


@pytest.mark.unit
@pytest.mark.security
class TestPythonASTValidator:
    """Test suite for Python AST validator"""

    def test_safe_code_passes(self, python_validator):
        """Test that safe Python code passes validation"""
        safe_codes = [
            "print('Hello, World!')",
            "x = 1 + 2",
            "def foo(): return 42",
            "for i in range(10): print(i)",
            "[x**2 for x in range(10)]",
            "import math\nprint(math.pi)",  # math is allowed
        ]

        for code in safe_codes:
            is_valid, message = python_validator.validate(code)
            assert is_valid, f"Safe code rejected: {code}\nReason: {message}"

    def test_blocked_operations_detected(self, python_validator):
        """Test detection of blocked operations"""
        blocked_codes = [
            ("eval('1+1')", "eval"),
            ("exec('print(1)')", "exec"),
            ("compile('1+1', '<string>', 'eval')", "compile"),
            ("__import__('os')", "__import__"),
            ("open('file.txt')", "open"),
            ("globals()", "globals"),
            ("locals()", "locals"),
        ]

        for code, expected_blocked in blocked_codes:
            is_valid, message = python_validator.validate(code)
            assert not is_valid, f"Dangerous code not detected: {code}"
            assert expected_blocked.lower() in message.lower(), \
                f"Expected '{expected_blocked}' in error message, got: {message}"

    def test_blocked_modules_detected(self, python_validator):
        """Test detection of blocked module imports"""
        blocked_imports = [
            ("import os", "os"),
            ("import sys", "sys"),
            ("import subprocess", "subprocess"),
            ("import socket", "socket"),
            ("from os import system", "os"),
            ("from subprocess import run", "subprocess"),
        ]

        for code, expected_module in blocked_imports:
            is_valid, message = python_validator.validate(code)
            assert not is_valid, f"Dangerous import not detected: {code}"
            assert expected_module in message.lower(), \
                f"Expected '{expected_module}' in error message, got: {message}"

    def test_dunder_attribute_access_blocked(self, python_validator):
        """Test blocking of dangerous dunder attribute access"""
        dangerous_codes = [
            "x.__builtins__",
            "[].__class__.__bases__",
            "x.__dict__",
            "x.__import__",
        ]

        for code in dangerous_codes:
            is_valid, message = python_validator.validate(code)
            # These should be caught
            if not is_valid:
                assert "dunder" in message.lower() or "attribute" in message.lower()

    def test_safe_dunder_methods_allowed(self, python_validator):
        """Test that safe dunder methods are allowed"""
        safe_codes = [
            "str(x)",  # Uses __str__
            "len([1,2,3])",  # Uses __len__
            "repr(x)",  # Uses __repr__
        ]

        for code in safe_codes:
            is_valid, message = python_validator.validate(code)
            assert is_valid, f"Safe code rejected: {code}\nReason: {message}"

    def test_syntax_error_detected(self, python_validator):
        """Test detection of syntax errors"""
        invalid_codes = [
            "print('unclosed string",
            "def foo(:\n    pass",
            "for i in",
        ]

        for code in invalid_codes:
            is_valid, message = python_validator.validate(code)
            assert not is_valid
            assert "syntax" in message.lower()

    def test_module_attribute_access_blocked(self, python_validator):
        """Test blocking of access to blocked module attributes"""
        dangerous_codes = [
            "import os\nos.system('ls')",  # Import blocked
            "import sys\nsys.exit()",  # Import blocked
        ]

        for code in dangerous_codes:
            is_valid, message = python_validator.validate(code)
            assert not is_valid, f"Dangerous code not detected: {code}"

    def test_subscript_dunder_access_blocked(self, python_validator):
        """Test blocking of subscript access to dunder variables"""
        dangerous_codes = [
            "__builtins__['eval']",
            "__dict__['x']",
        ]

        for code in dangerous_codes:
            is_valid, message = python_validator.validate(code)
            assert not is_valid, f"Dangerous code not detected: {code}"
            assert "subscript" in message.lower() or "dunder" in message.lower()


@pytest.mark.unit
@pytest.mark.security
class TestPythonValidatorEdgeCases:
    """Test edge cases for Python validator"""

    def test_empty_code(self, python_validator):
        """Test validation of empty code"""
        is_valid, message = python_validator.validate("")
        # Empty code is technically valid Python
        assert is_valid

    def test_comments_only(self, python_validator):
        """Test code with only comments"""
        code = "# This is a comment\n# Another comment"
        is_valid, message = python_validator.validate(code)
        assert is_valid

    def test_multiline_string(self, python_validator):
        """Test code with multiline strings"""
        code = '''
"""
This is a docstring
"""
print("Hello")
'''
        is_valid, message = python_validator.validate(code)
        assert is_valid

    def test_complex_safe_code(self, python_validator):
        """Test complex but safe Python code"""
        code = """
class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, x):
        self.result += x
        return self.result

calc = Calculator()
for i in range(10):
    calc.add(i)

print(calc.result)
"""
        is_valid, message = python_validator.validate(code)
        assert is_valid, f"Complex safe code rejected. Reason: {message}"
