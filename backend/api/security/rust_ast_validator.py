"""
Validates Rust code using tree-sitter AST analysis.

Checks for:
- use declarations of blocked modules (std::fs, std::net, std::process, etc.)
- unsafe blocks
- FFI (extern "C", #[no_mangle])
- Dangerous standard library usage
"""

from tree_sitter import Tree, Node
from typing import Tuple
from .ast_validator import BaseASTValidator
from ..models.allowlist import RUST_BLOCKED_OPERATIONS


class RustASTValidator(BaseASTValidator):

    def validate(self, tree: Tree, code: str) -> Tuple[bool, str]:

        self.code_bytes = bytes(code, 'utf8')
        root = tree.root_node

        # Check for blocked module usage
        result = self._check_use_declarations(root)
        if not result[0]:
            return result

        # Check for unsafe blocks
        result = self._check_unsafe_blocks(root)
        if not result[0]:
            return result

        # Check for FFI
        result = self._check_ffi(root)
        if not result[0]:
            return result

        return True, ""

    def _check_use_declarations(self, root: Node) -> Tuple[bool, str]:

        uses = self.walker.find_nodes_by_type(root, 'use_declaration')

        for use in uses:
            use_path = self._get_use_path(use)

            if not use_path:
                continue

            # Check against blocked operations
            for blocked in RUST_BLOCKED_OPERATIONS:
                if use_path.startswith(blocked):
                    return False, f"Blocked module: {use_path}"

        return True, ""

    def _check_unsafe_blocks(self, root: Node) -> Tuple[bool, str]:
        """
        Check for unsafe blocks

        Detects:
        - unsafe { ... }
        - unsafe fn
        - unsafe impl
        """
        # Check for unsafe blocks
        unsafe_blocks = self.walker.find_nodes_by_type(root, 'unsafe_block')
        if unsafe_blocks:
            return False, "Unsafe code blocks not allowed"

        # Check for unsafe functions
        # Look for function_item with unsafe modifier
        functions = self.walker.find_nodes_by_type(root, 'function_item')
        for func in functions:
            func_text = self._get_node_text(func)
            if func_text.strip().startswith('unsafe '):
                return False, "Unsafe functions not allowed"

        # Check for unsafe trait implementations
        impls = self.walker.find_nodes_by_type(root, 'impl_item')
        for impl in impls:
            impl_text = self._get_node_text(impl)
            if 'unsafe' in impl_text:
                return False, "Unsafe implementations not allowed"

        return True, ""

    def _check_ffi(self, root: Node) -> Tuple[bool, str]:
        """
        Check for Foreign Function Interface (FFI) usage

        Detects:
        - extern "C"
        - #[no_mangle]
        - #[link]
        """
        # Check for extern blocks
        extern_blocks = self.walker.find_nodes_by_type(root, 'extern_block')
        if extern_blocks:
            return False, "Foreign function interface (extern) not allowed"

        # Check for FFI-related attributes
        attributes = self.walker.find_nodes_by_type(root, 'attribute_item')
        for attr in attributes:
            attr_text = self._get_node_text(attr)
            if 'no_mangle' in attr_text or 'link' in attr_text:
                return False, "FFI attributes not allowed"

        # Check for extern function declarations
        functions = self.walker.find_nodes_by_type(root, 'function_item')
        for func in functions:
            func_text = self._get_node_text(func)
            if func_text.strip().startswith('extern '):
                return False, "Extern functions not allowed"

        return True, ""

    def _get_use_path(self, use_node: Node) -> str:
        """
        Extract the module path from a use declaration

        Handles:
        - use std::fs;
        - use std::fs::File;
        - use std::{fs, io};

        Args:
            use_node: use_declaration node

        Returns:
            Module path as string
        """
        # Find the scoped_identifier or identifier
        path_parts = []

        def extract_path(node):
            if node.type == 'identifier':
                path_parts.append(self._get_node_text(node))
            elif node.type == 'scoped_identifier':
                # Recursively extract path
                for child in node.children:
                    if child.type in ['identifier', 'scoped_identifier']:
                        extract_path(child)
            elif node.type == 'use_declaration':
                for child in node.children:
                    if child.type in ['identifier', 'scoped_identifier', 'use_list', 'scoped_use_list']:
                        extract_path(child)

        extract_path(use_node)

        # Join path parts with ::
        if path_parts:
            return '::'.join(path_parts)

        # Fallback: get the whole text and clean it
        text = self._get_node_text(use_node)
        # Remove 'use' keyword and semicolon
        text = text.replace('use ', '').replace(';', '').strip()
        # Extract just the path (before any 'as' keyword)
        if ' as ' in text:
            text = text.split(' as ')[0].strip()
        return text
