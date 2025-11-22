from typing import List
from .base import BaseExecutor


class PythonExecutor(BaseExecutor):
    """Python code executor"""

    def _build_command(self, filepath: str, workdir: str) -> List[str]:
        return ["python3", filepath]
