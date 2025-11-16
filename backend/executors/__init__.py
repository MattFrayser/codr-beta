from .base import BaseExecutor
from .compiled_base import CompiledExecutor
from .python import PythonExecutor
from .javascript import JavaScriptExecutor
from .rust import RustExecutor
from .c import CExecutor
from .cpp import CppExecutor

EXECUTORS = {
    'python': PythonExecutor,
    'javascript': JavaScriptExecutor,
    'rust': RustExecutor,
    'c': CExecutor,
    'cpp': CppExecutor,
    'c++': CppExecutor,  # Alias for cpp
}

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "c": ".c",
    "cpp": ".cpp",
    "rust": ".rs"
}

def get_default_filename(language: str) -> str:
    return f"main{LANGUAGE_EXTENSIONS.get(language, '.txt')}"



def get_executor(language: str) -> BaseExecutor:
    """
    Get executor instance for the specified language

    Args:
        language: Programming language name (lowercase)

    Returns:
        BaseExecutor instance for the language

    Raises:
        ValueError: If language is not supported
    """
    language = language.lower().strip()
    executor_class = EXECUTORS.get(language)

    if not executor_class:
        supported = ', '.join(sorted(set(EXECUTORS.keys())))
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Supported languages: {supported}"
        )

    return executor_class()


def get_supported_languages() -> set:
    """
    Get set of all supported languages

    Returns:
        Set of supported language names (lowercase)

    Example:
        >>> languages = get_supported_languages()
        >>> 'python' in languages
        True
    """
    return set(EXECUTORS.keys())


