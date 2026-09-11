import os
import json
from groq import Groq
from .log_analyzer import ErrorInfo

MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are CodeAutopsy, an expert software engineer AI that fixes build \
and test failures. You will be given an error traceback and the relevant source file. \
Respond ONLY with valid JSON (no markdown fences, no preamble, no trailing text) matching \
this schema:

{
  "root_cause": "1-3 sentence explanation of WHY the error happened",
  "fix_explanation": "1-2 sentence explanation of WHAT the fix changes and why it resolves it",
  "fixed_file_content": "the COMPLETE corrected file content, ready to overwrite the original file",
  "pr_title": "a short, conventional-commit style PR title, e.g. 'fix: handle empty list in parse_items'",
  "confidence": "high | medium | low"
}

Rules:
- Preserve all unrelated code exactly as-is; change only what's needed to fix the bug.
- Keep the original code style/formatting conventions.
- If you cannot confidently fix it, still return your best attempt but set confidence to "low" \
and explain the uncertainty in fix_explanation.
- Output raw JSON only. Do not wrap it in ```json fences.
"""


def _build_user_prompt(error: ErrorInfo, context: dict) -> str:
    parts = [
        f"ERROR TYPE: {error.error_type}",
        f"MESSAGE: {error.message}",
        f"FILE: {error.file_path}",
        f"LINE: {error.line_number}",
        f"FUNCTION: {error.function_name}",
        "",
        "RAW TRACEBACK:",
        error.raw_traceback,
    ]
    if context.get("full_file"):
        parts += ["", "FULL FILE CONTENT:", context["full_file"]]
    elif context.get("snippet"):
        parts += ["", "CODE SNIPPET AROUND FAILURE:", context["snippet"]]
    else:
        parts += ["", "NOTE: source file could not be located in the repo checkout."]
    return "\n".join(parts)


def generate_fix(error: ErrorInfo, context: dict, api_key: str = None) -> dict:

    client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4000,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(error, context)},
        ],
    )

    raw_text = response.choices[0].message.content
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {
            "root_cause": "AI response could not be parsed as JSON.",
            "fix_explanation": raw_text[:500],
            "fixed_file_content": context.get("full_file", ""),
            "pr_title": "fix: automated fix (unparsed response)",
            "confidence": "low",
        }
    return result
