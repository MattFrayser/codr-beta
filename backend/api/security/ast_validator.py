"""
AST-based code validation using tree-sitter

This module provides infrastructure for parsing and validating code using
Abstract Syntax Tree (AST) analysis via tree-sitter. This is significantly
more accurate than regex-based validation and harder to bypass with obfuscation.
"""

from tree_sitter import Language, Parser, Node, Tree
from typing import Tuple, List, Callable, Optional
from abc import ABC, abstractmethod

import tree_sitter_javascript as ts_javascript
import tree_sitter_c as ts_c
import tree_sitter_cpp as ts_cpp
import tree_sitter_rust as ts_rust

class TreeSitterParser:
    """
    Manages tree-sitter parsers for multiple languages

    Provides a unified interface for parsing code in different languages
    using tree-sitter's language-specific parsers.
    """

    def __init__(self):
        """Initialize parsers for all supported languages"""
        self.parsers = {}
        self.languages = {}
        self._load_languages()

    def _load_languages(self):
        """Load language grammars and create parsers"""
        language_modules = {
            'javascript': ts_javascript,
            'js': ts_javascript,
            'c': ts_c,
            'cpp': ts_cpp,
            'c++': ts_cpp,
            'rust': ts_rust,
        }

        for lang_key, module in language_modules.items():
            try:
                language = Language(module.language(), name=lang_key)
                parser = Parser(language)
                self.languages[lang_key] = language
                self.parsers[lang_key] = parser
            except Exception as e:
                print(f"Failed to load {lang_key} parser: {e}")

    def parse(self, code: str, language: str) -> Tree:
        """
        Parse code and return AST

        Args:
            code: Source code to parse
            language: Programming language (javascript, c, cpp, rust)

        Returns:
            tree-sitter Tree object

        Raises:
            ValueError: If language is not supported
            Exception: If parsing fails
        """
        language = language.lower()

        if language not in self.parsers:
            raise ValueError(f"Unsupported language for AST parsing: {language}")

        parser = self.parsers[language]
        tree = parser.parse(bytes(code, 'utf8'))

        if tree.root_node.has_error:
            raise Exception("Syntax error in code")

        return tree


class ASTWalker:
    """
    Generic AST tree walker

    Provides utility methods for traversing and querying tree-sitter ASTs.
    """

    @staticmethod
    def walk(node: Node, callback: Callable[[Node], None]):
        """
        Recursively traverse AST and call callback on each node

        Args:
            node: Root node to start traversal
            callback: Function to call on each node
        """
        callback(node)
        for child in node.children:
            ASTWalker.walk(child, callback)

    @staticmethod
    def find_nodes_by_type(root: Node, node_type: str) -> List[Node]:
        """
        Find all nodes of a specific type in the AST

        Args:
            root: Root node to search from
            node_type: Type of nodes to find (e.g., 'call_expression')

        Returns:
            List of matching nodes
        """
        results = []

        def collector(node):
            if node.type == node_type:
                results.append(node)

        ASTWalker.walk(root, collector)
        return results

    @staticmethod
    def find_nodes_by_types(root: Node, node_types: List[str]) -> List[Node]:
        """
        Find all nodes matching any of the specified types

        Args:
            root: Root node to search from
            node_types: List of node types to find

        Returns:
            List of matching nodes
        """
        results = []
        node_types_set = set(node_types)

        def collector(node):
            if node.type in node_types_set:
                results.append(node)

        ASTWalker.walk(root, collector)
        return results

    @staticmethod
    def get_node_text(node: Node, code: bytes) -> str:
        """
        Get the source code text for a node

        Args:
            node: AST node
            code: Original source code as bytes

        Returns:
            Text content of the node
        """
        return code[node.start_byte:node.end_byte].decode('utf8')

    @staticmethod
    def find_child_by_type(node: Node, child_type: str) -> Optional[Node]:
        """
        Find first direct child of specified type

        Args:
            node: Parent node
            child_type: Type of child to find

        Returns:
            First matching child node, or None
        """
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    @staticmethod
    def find_child_by_field(node: Node, field_name: str) -> Optional[Node]:
        """
        Find child by field name

        Args:
            node: Parent node
            field_name: Name of field

        Returns:
            Child node for the field, or None
        """
        return node.child_by_field_name(field_name)


class BaseASTValidator(ABC):
    """
    Base class for language-specific AST validators

    Subclasses implement language-specific validation logic
    by overriding the validate() method.
    """

    def __init__(self):
        self.walker = ASTWalker()
        self.code_bytes = b""

    @abstractmethod
    def validate(self, tree: Tree, code: str) -> Tuple[bool, str]:
        """
        Validate code using AST analysis

        Args:
            tree: Parsed AST tree
            code: Original source code

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if code is safe
            - (False, "error message") if code is dangerous
        """
        pass

    def _get_node_text(self, node: Node) -> str:
        """Get text content of a node"""
        return self.walker.get_node_text(node, self.code_bytes)

    def _find_child_by_type(self, node: Node, child_type: str) -> Optional[Node]:
        """Find first child of specified type"""
        return self.walker.find_child_by_type(node, child_type)

    def _find_child_by_field(self, node: Node, field_name: str) -> Optional[Node]:
        """Find child by field name"""
        return self.walker.find_child_by_field(node, field_name)
