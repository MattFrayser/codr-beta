from typing import List, Tuple
from .compiled_base import CompiledExecutor


class CExecutor(CompiledExecutor):
    """C code executor with gcc compilation"""

    def _get_compiler_config(self) -> Tuple[str, List[str]]:
        compiler = "gcc"
        flags = ["-std=c11", "-lm"]  # C11 standard, link math library
        return (compiler, flags)
