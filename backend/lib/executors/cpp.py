from typing import List, Tuple
from .compiled_base import CompiledExecutor


class CppExecutor(CompiledExecutor):
    """C++ code executor with g++ compilation"""

    def _get_compiler_config(self) -> Tuple[str, List[str]]:
        compiler = "g++"
        flags = ["-std=c++17", "-lstdc++"]  # C++17 standard, link C++ stdlib
        return (compiler, flags)
