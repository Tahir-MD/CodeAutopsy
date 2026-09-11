"""
log_analyzer.py
----------------
Parses build/CI error logs (Python tracebacks, pytest failures, generic
stack traces) into structured data the rest of CodeAutopsy can act on.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ErrorInfo:
    error_type: str
    message: str
    file_path: Optional[str]
    line_number: Optional[int]
    raw_traceback: str
    function_name: Optional[str] = None
    related_frames: List[str] = field(default_factory=list)


# Matches lines like: File "path/to/file.py", line 42, in some_function
FRAME_RE = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)')

# Matches the final "ExceptionType: message" line of a Python traceback
FINAL_ERROR_RE = re.compile(r'^(?P<etype>[\w\.]+Error|[\w\.]+Exception)\s*:\s*(?P<msg>.*)$', re.MULTILINE)

# Matches pytest-style "FAILED path::test_name - ErrorType: message"
PYTEST_RE = re.compile(r'FAILED (?P<file>\S+)::(?P<func>\S+)\s*-\s*(?P<etype>[\w\.]+)\s*:\s*(?P<msg>.*)')


def parse_log(log_text: str) -> ErrorInfo:
    """
    Extracts the most actionable error from a raw log string.
    Falls back gracefully if the format isn't a classic traceback.
    """
    log_text = log_text.strip()

    # Try pytest summary line first (common in CI output)
    pytest_match = PYTEST_RE.search(log_text)
    if pytest_match:
        return ErrorInfo(
            error_type=pytest_match.group("etype"),
            message=pytest_match.group("msg").strip(),
            file_path=pytest_match.group("file"),
            line_number=None,
            function_name=pytest_match.group("func"),
            raw_traceback=log_text,
        )

    # Try classic Python traceback
    frames = FRAME_RE.findall(log_text)
    final_match = None
    for m in FINAL_ERROR_RE.finditer(log_text):
        final_match = m  # keep the last match (real error, not a re-raised one)

    if frames:
        last_file, last_line, last_func = frames[-1]
        error_type = final_match.group("etype") if final_match else "UnknownError"
        message = final_match.group("msg").strip() if final_match else "No message captured"
        related = [f'{f} (line {l}, in {fn})' for f, l, fn in frames]
        return ErrorInfo(
            error_type=error_type,
            message=message,
            file_path=last_file,
            line_number=int(last_line),
            function_name=last_func,
            related_frames=related,
            raw_traceback=log_text,
        )

    # Fallback: no recognizable structure, return raw text for the AI to reason about
    return ErrorInfo(
        error_type="Unstructured",
        message=log_text[:300],
        file_path=None,
        line_number=None,
        raw_traceback=log_text,
    )
