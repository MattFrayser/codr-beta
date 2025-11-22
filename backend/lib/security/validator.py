"""
Code security validator using AST analysis for all languages.

AST analysis provides significantly better accuracy than regex-based validation
and is much harder to bypass with obfuscation techniques.

Goal is to block known dangerous patterns via AST analysis.
Firejail sandbox provides the primary security boundary.
"""

from typing import Tuple

from .ast_validator import TreeSitterParser
from .python_ast_validator import PythonASTValidator
from .javascript_ast_validator import JavaScriptASTValidator
from .c_cpp_ast_validator import CCppASTValidator
from .rust_ast_validator import RustASTValidator


class CodeValidator:
    """Validates code against security blocklists using AST analysis"""

    def __init__(self):
        self.ts_parser = TreeSitterParser()
        self.python_validator = PythonASTValidator()
        self.js_validator = JavaScriptASTValidator()
        self.c_validator = CCppASTValidator()
        self.rust_validator = RustASTValidator()

    @staticmethod
    def validate(code: str, language: str) -> Tuple[bool, str]:
        """
        Validate code is safe to execute

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            Exception if tree-sitter is not available or parsing fails
        """
        # Create validator instance
        validator = CodeValidator()
        language = language.lower()

        # Dispatch to appropriate validator
        if language == "python":
            return validator.python_validator.validate(code)
        elif language in ["javascript", "js"]:
            tree = validator.ts_parser.parse(code, "javascript")
            return validator.js_validator.validate(tree, code)
        elif language in ["c", "cpp", "c++"]:
            tree = validator.ts_parser.parse(code, "cpp")
            return validator.c_validator.validate(tree, code)
        elif language == "rust":
            tree = validator.ts_parser.parse(code, "rust")
            return validator.rust_validator.validate(tree, code)
        else:
            return False, f"Unsupported language: {language}"
