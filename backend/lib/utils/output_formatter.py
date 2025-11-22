"""
Output formatting utilities to clean error messages
"""

import re
from typing import Tuple


# like [90m, [39m, [1;31m
def strip_ansi_codes(text: str) -> str:

    # Pattern matches all ANSI escape sequences
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m|\[[\d;]+m")
    return ansi_pattern.sub("", text)


# Replace full temp paths with just the filename
# /private/var/folders/.../tmp123/main.js -> main.js
def clean_file_paths(text: str, workdir: str) -> str:

    text = re.sub(rf"{re.escape(workdir)}/?", "", text)

    # Also clean common temp path patterns
    text = re.sub(r"/private/var/folders/[^/]+/[^/]+/[^/]+/[^/]+/", "", text)
    text = re.sub(r"/var/folders/[^/]+/[^/]+/[^/]+/[^/]+/", "", text)
    text = re.sub(r"/tmp/[^/]+/", "", text)

    return text


# Filter out internal/verbose stack trace lines
def filter_stack_trace(text: str, language: str) -> str:

    lines = text.split("\n")
    filtered_lines: list[str] = []

    if language == "javascript":
        # Keep only relevant lines for JavaScript errors
        skip_patterns = [
            r"at Module\._compile",
            r"at Object\.\.js",
            r"at Module\.load",
            r"at Function\._load",
            r"at TracingChannel",
            r"at wrapModuleLoad",
            r"at Function\.executeUserEntryPoint",
            r"at node:internal",
            r"Node\.js v\d+\.",  # Version line
        ]

        for line in lines:
            # Skip internal Node.js lines
            if any(re.search(pattern, line) for pattern in skip_patterns):
                continue
            # Skip empty lines after filtering
            if line.strip() or filtered_lines:  # Keep first line even if empty
                filtered_lines.append(line)

    elif language == "python":
        # Keep only relevant lines for Python errors
        skip_patterns = [
            r"File.*site-packages",  # Skip library internals
        ]

        for line in lines:
            # Detect start of traceback
            if line.startswith("Traceback"):
                filtered_lines.append(line)
                continue

            # Skip internal library lines
            if any(re.search(pattern, line) for pattern in skip_patterns):
                continue

            filtered_lines.append(line)
    else:
        # other languages return as-is
        return text

    return "\n".join(filtered_lines).strip()


def format_error_message(text: str, language: str, workdir: str) -> str:

    text = strip_ansi_codes(text)

    text = clean_file_paths(text, workdir)

    text = filter_stack_trace(text, language)

    # excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 newlines
    text = text.strip()

    return text


# Extract a short error summary and full details
def extract_error_summary(text: str, language: str) -> Tuple[str, str]:

    lines = text.split("\n")
    summary = ""

    if language == "javascript":
        # Find the error line
        for line in lines:
            if "Error:" in line and not line.strip().startswith("at"):
                summary = line.strip()
                break

    elif language == "python":
        # Find exception line
        for i, line in enumerate(lines):
            if i > 0 and ":" in line and not line.startswith(" "):
                # This is likely the exception line
                summary = line.strip()
                break

    if not summary:
        # Fallback: first non-empty line
        summary = next((line.strip() for line in lines if line.strip()), "Error")

    return summary, text
