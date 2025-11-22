from typing import List
from .base import BaseExecutor


class JavaScriptExecutor(BaseExecutor):
    """JavaScript/Node.js code executor"""

    def _build_command(self, filepath: str, workdir: str) -> List[str]:
        return [
            "node",
            "--max-old-space-size=64",  # 64MB heap limit
            "--no-concurrent-recompilation",
            "--single-threaded-gc",
            filepath,
        ]
