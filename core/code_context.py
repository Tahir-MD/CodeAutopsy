import os
from typing import Optional
from .log_analyzer import ErrorInfo

MAX_FILE_CHARS = 12000  # keep prompt sizes sane for large files


def read_file_safe(repo_path: str, relative_or_abs_path: str) -> Optional[str]:
    candidates = [
        relative_or_abs_path,
        os.path.join(repo_path, relative_or_abs_path),
        os.path.join(repo_path, os.path.basename(relative_or_abs_path)),
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + "\n# ... [truncated] ..."
            return content
    return None


def get_windowed_snippet(file_content: str, line_number: int, window: int = 25) -> str:
    lines = file_content.splitlines()
    start = max(0, line_number - window - 1)
    end = min(len(lines), line_number + window)
    numbered = [f"{i + 1}: {lines[i]}" for i in range(start, end)]
    return "\n".join(numbered)


def build_context(repo_path: str, error: ErrorInfo) -> dict:

    context = {
        "file_path": error.file_path,
        "full_file": None,
        "snippet": None,
        "found": False,
    }

    if not error.file_path:
        return context

    content = read_file_safe(repo_path, error.file_path)
    if content is None:
        return context

    context["found"] = True
    context["full_file"] = content

    if error.line_number:
        context["snippet"] = get_windowed_snippet(content, error.line_number)

    return context
