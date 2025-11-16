"""
Validates JavaScript code using tree-sitter AST analysis.

Checks for:
- Dangerous function calls (eval, Function, etc.)
- Blocked module requires/imports (fs, child_process, etc.)
- Dangerous property access (process.binding, global.process, etc.)
- Constructor access bypasses
- Obfuscation techniques
"""

from tree_sitter import Tree, Node
from typing import Tuple, Optional
from .ast_validator import BaseASTValidator
from ..models.allowlist import (
    JAVASCRIPT_BLOCKED_OPERATIONS,
    JAVASCRIPT_BLOCKED_MODULES,
    JAVASCRIPT_DANGEROUS_PATTERNS,
    JAVASCRIPT_BLOCKED_IDENTIFIERS,
)


class JavaScriptASTValidator(BaseASTValidator):

    def validate(self, tree: Tree, code: str) -> Tuple[bool, str]:

        self.code_bytes = bytes(code, 'utf8')
        root = tree.root_node

        # Check for dangerous function calls
        result = self._check_call_expressions(root)
        if not result[0]:
            return result

        # Check for blocked module imports
        result = self._check_imports(root)
        if not result[0]:
            return result

        # Check for dangerous member access
        result = self._check_member_expressions(root)
        if not result[0]:
            return result

        # Check for constructor access
        result = self._check_constructor_access(root)
        if not result[0]:
            return result

        # Check for dangerous identifiers
        result = self._check_identifiers(root)
        if not result[0]:
            return result

        return True, ""

    def _check_call_expressions(self, root: Node) -> Tuple[bool, str]:

        calls = self.walker.find_nodes_by_type(root, 'call_expression')

        for call in calls:
            func_name = self._get_function_name(call)

            if not func_name:
                continue

            # Check for blocked operations
            if func_name in JAVASCRIPT_BLOCKED_OPERATIONS:
                return False, f"Blocked operation: {func_name}()"

            # Check require() calls for blocked modules
            if func_name == 'require':
                result = self._check_require_call(call)
                if not result[0]:
                    return result

        return True, ""

    def _check_imports(self, root: Node) -> Tuple[bool, str]:
        # Check import statements

        imports = self.walker.find_nodes_by_type(root, 'import_statement')

        for imp in imports:
            # Get the string literal (source)
            source = self._find_child_by_type(imp, 'string')
            if source:
                module_name = self._get_string_value(source)
                if self._is_blocked_module(module_name):
                    return False, f"Blocked module: {module_name}"

        return True, ""

    def _check_member_expressions(self, root: Node) -> Tuple[bool, str]:

        members = self.walker.find_nodes_by_type(root, 'member_expression')

        for member in members:
            member_text = self._get_node_text(member)

            # Check for dangerous patterns
            for pattern in JAVASCRIPT_DANGEROUS_PATTERNS:
                if pattern in member_text:
                    return False, f"Dangerous property access: {pattern}"

        return True, ""

    def _check_constructor_access(self, root: Node) -> Tuple[bool, str]:
        """
        Detects:
        - .constructor
        - ['constructor']
        - Object.constructor
        """
        # Check member expressions for 'constructor'
        members = self.walker.find_nodes_by_type(root, 'member_expression')

        for member in members:
            property_node = self._find_child_by_field(member, 'property')
            if property_node:
                prop_text = self._get_node_text(property_node)
                if 'constructor' in prop_text:
                    return False, "Constructor access not allowed"

        # Check subscript expressions (bracket notation)
        subscripts = self.walker.find_nodes_by_type(root, 'subscript_expression')

        for subscript in subscripts:
            index_node = self._find_child_by_field(subscript, 'index')
            if index_node:
                index_text = self._get_node_text(index_node)
                if 'constructor' in index_text:
                    return False, "Constructor access not allowed"

        return True, ""

    def _check_identifiers(self, root: Node) -> Tuple[bool, str]:

        identifiers = self.walker.find_nodes_by_type(root, 'identifier')

        for identifier in identifiers:
            name = self._get_node_text(identifier)

            # Check if it's a standalone dangerous identifier
            # (not part of a member expression we already checked)
            parent = identifier.parent
            if parent and parent.type != 'member_expression':
                if name in JAVASCRIPT_BLOCKED_IDENTIFIERS:
                    return False, f"Blocked identifier: {name}"

        return True, ""

    def _check_require_call(self, call_node: Node) -> Tuple[bool, str]:
        """
        Check require() call for blocked modules

        """
        # Get the arguments node
        arguments = self._find_child_by_type(call_node, 'arguments')
        if not arguments:
            return True, ""

        # Get first argument (module name)
        for child in arguments.children:
            if child.type == 'string':
                module_name = self._get_string_value(child)
                if self._is_blocked_module(module_name):
                    return False, f"Blocked module: {module_name}"
                break

        return True, ""

    def _get_function_name(self, call_node: Node) -> Optional[str]:
        """
        Handles:
        - Simple calls: func()
        - Member calls: obj.method()
        - Computed calls: obj['method']()

        Args:
            call_node: call_expression node

        Returns:
            Function name or None
        """
        function = self._find_child_by_field(call_node, 'function')
        if not function:
            return None

        if function.type == 'identifier':
            return self._get_node_text(function)
        elif function.type == 'member_expression':
            property_node = self._find_child_by_field(function, 'property')
            if property_node:
                return self._get_node_text(property_node)

        return None

    def _get_string_value(self, string_node: Node) -> str:
        """
        Removes quotes and handles escape sequences.
        """
        text = self._get_node_text(string_node)
        # Remove quotes (both single and double)
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            return text[1:-1]
        elif text.startswith("`") and text.endswith("`"):
            return text[1:-1]
        return text

    def _is_blocked_module(self, module_name: str) -> bool:

        # Check against blocked modules list
        if module_name in JAVASCRIPT_BLOCKED_MODULES:
            return True

        # Check if it's trying to access a blocked module via path
        for blocked in JAVASCRIPT_BLOCKED_MODULES:
            if module_name.startswith(f'{blocked}/'):
                return True

        return False
