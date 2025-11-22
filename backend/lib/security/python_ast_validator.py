"""
Python AST Validator - validates Python code using built-in AST module.

"""

import ast
from typing import Tuple
from ..models.allowlist import (
    PYTHON_BLOCKED_OPERATIONS,
    PYTHON_BLOCKED_MODULES,
    PYTHON_SAFE_DUNDERS,
)


class PythonASTValidator:
    """Validates Python code using AST analysis"""

    def validate(self, code: str) -> Tuple[bool, str]:

        # Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"

        # Check for blocked operations using AST
        for node in ast.walk(tree):
            # Check for blocked built-in functions
            if isinstance(node, ast.Call):
                # Direct function calls: eval(), exec(), etc.
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in PYTHON_BLOCKED_OPERATIONS:
                        return False, f"Blocked operation: {func_name}()"

                # Attribute access function calls: obj.method()
                elif isinstance(node.func, ast.Attribute):
                    # Block any access to __builtins__ or similar
                    if node.func.attr.startswith("__") and node.func.attr.endswith(
                        "__"
                    ):
                        return (
                            False,
                            f"Blocked dunder method access: {node.func.attr}()",
                        )

            # Check imports - both import and from...import
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split(".")[0]
                        if module in PYTHON_BLOCKED_MODULES:
                            return False, f"Blocked module: {module}"

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split(".")[0]
                        if module in PYTHON_BLOCKED_MODULES:
                            return False, f"Blocked module: {module}"

            # Check for attribute access to blocked modules or builtins
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    # Block access to blocked modules
                    if node.value.id in PYTHON_BLOCKED_MODULES:
                        return False, f"Access to blocked module: {node.value.id}"
                    # Block __builtins__ and similar
                    if node.value.id.startswith("__") and node.value.id.endswith("__"):
                        return False, f"Access to dunder variable: {node.value.id}"
                    # Block special attributes
                    if node.attr.startswith("__") and node.attr.endswith("__"):
                        # Allow some safe dunder methods
                        if node.attr not in PYTHON_SAFE_DUNDERS:
                            return False, f"Access to restricted attribute: {node.attr}"

            # Check for subscript access (like __builtins__['eval'])
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name):
                    if node.value.id.startswith("__") and node.value.id.endswith("__"):
                        return (
                            False,
                            f"Subscript access to dunder variable: {node.value.id}",
                        )

            # Block compile() which can bypass checks
            if isinstance(node, ast.Name):
                if node.id == "compile":
                    return False, "Blocked operation: compile"

        return True, ""
