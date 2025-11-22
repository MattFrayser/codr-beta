"""
Infrastructure for parsing and validating code using
Abstract Syntax Tree (AST) analysis via tree-sitter.
Significantly more accurate than regex-based validation.
"""

from tree_sitter import Language, Parser, Node, Tree
from typing import Tuple, List, Callable, Optional
from abc import ABC, abstractmethod

import tree_sitter_javascript as ts_javascript
import tree_sitter_c as ts_c
import tree_sitter_cpp as ts_cpp
import tree_sitter_rust as ts_rust


class TreeSitterParser:

    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self._load_languages()

    def _load_languages(self):
        language_modules = {
            "javascript": ts_javascript,
            "js": ts_javascript,
            "c": ts_c,
            "cpp": ts_cpp,
            "c++": ts_cpp,
            "rust": ts_rust,
        }

        for lang_key, module in language_modules.items():
            try:
                language = Language(module.language(), name=lang_key)
                parser = Parser()
                parser.set_language(language)
                self.languages[lang_key] = language
                self.parsers[lang_key] = parser
            except Exception as e:
                print(f"Failed to load {lang_key} parser: {e}")

    def parse(self, code: str, language: str) -> Tree:
        """
        Parse code and return AST

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
        tree = parser.parse(bytes(code, "utf8"))

        if tree.root_node.has_error:
            raise Exception("Syntax error in code")

        return tree


class ASTWalker:
    """
    Utility methods for traversing and querying tree-sitter ASTs.
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
        return code[node.start_byte:node.end_byte].decode("utf8")

    @staticmethod
    def find_child_by_type(node: Node, child_type: str) -> Optional[Node]:
        """
        Find first direct child of specified type

        Returns:
            First matching child node, or None
        """
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    @staticmethod
    def find_child_by_field(node: Node, field_name: str) -> Optional[Node]:
        return node.child_by_field_name(field_name)


class BaseASTValidator(ABC):
    """
    Base class for language-specific AST validators

    Subclasses override validate() method.
    """

    def __init__(self):
        self.walker = ASTWalker()
        self.code_bytes = b""

    @abstractmethod
    def validate(self, tree: Tree, code: str) -> Tuple[bool, str]:
        """
        Returns:
            (is_valid, error_message)
        """
        pass

    def _get_node_text(self, node: Node) -> str:
        return self.walker.get_node_text(node, self.code_bytes)

    def _find_child_by_type(self, node: Node, child_type: str) -> Optional[Node]:
        return self.walker.find_child_by_type(node, child_type)

    def _find_child_by_field(self, node: Node, field_name: str) -> Optional[Node]:
        return self.walker.find_child_by_field(node, field_name)

    def _blocked_operation_error(self, name: str) -> Tuple[bool, str]:
        return False, f"Blocked operation {name}()"
