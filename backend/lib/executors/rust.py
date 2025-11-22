from typing import List, Tuple
from .compiled_base import CompiledExecutor


class RustExecutor(CompiledExecutor):
    """Rust code executor with rustc compilation"""

    def _get_compiler_config(self) -> Tuple[str, List[str]]:
        compiler = "rustc"
        flags: List[str] = []  # No additional flags needed for basic compilation
        return (compiler, flags)
