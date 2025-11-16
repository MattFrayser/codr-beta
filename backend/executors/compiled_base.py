"""
Base executor for compiled languages (C, C++, Rust)

Provides shared compilation logic to eliminate code duplication across
compiled language executors.
"""

import os
import subprocess
from typing import List, Tuple
from abc import abstractmethod
from .base import BaseExecutor


class CompiledExecutor(BaseExecutor):
    """
    Base class for compiled language executors
    Complies and returns executable path

    Subclasses must implement _get_compiler_config() to specify
    their compiler and compilation flags.
    """

    @abstractmethod
    def _get_compiler_config(self) -> Tuple[str, List[str]]:
        """
        Returns: Tuple of (compiler_path, compilation_flags)
        """
        pass

    def _build_command(self, filepath: str, workdir: str) -> List[str]:
        """ Compile source code and return executable path """
        compiler, flags = self._get_compiler_config()

        # output executable path
        binarypath = os.path.join(workdir, 'program')

        try:
            from config.settings import get_settings
            compilation_timeout = get_settings().compilation_timeout
        except (ImportError, Exception):
            compilation_timeout = 10  # Fallback default

        try:
            compile_result = subprocess.run(
                [compiler, filepath, '-o', binarypath] + flags,
                capture_output=True,
                text=True,
                cwd=workdir,
                timeout=compilation_timeout
            )

            if compile_result.returncode != 0:
                raise Exception(f"Compilation failed:\n{compile_result.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception(f"Compilation timed out after {compilation_timeout} seconds")

        # Return path to executable
        return [binarypath]
