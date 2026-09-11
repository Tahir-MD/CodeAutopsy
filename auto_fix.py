import os
import sys

from core.log_analyzer import parse_log
from core.code_context import build_context
from core.ai_fixer import generate_fix
from core.github_handler import run_full_pipeline


def main():
    repo_full_name = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    log_path = os.environ.get("CI_LOG_PATH")
    base_branch = os.environ.get("BASE_BRANCH", "main")

    if not all([repo_full_name, token, anthropic_key, log_path]):
        print("Missing required environment variables. See module docstring.")
        sys.exit(1)

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        log_text = f.read()

    error_info = parse_log(log_text)
    print(f"Parsed error: {error_info.error_type} in {error_info.file_path}:{error_info.line_number}")

    # We're already inside the checked-out repo in CI, so use "." as repo_path for context reading
    context = build_context(".", error_info)

    result = generate_fix(error_info, context, api_key=anthropic_key)
    print(f"Confidence: {result.get('confidence')}")

    if not context.get("found"):
        print("Could not locate the source file in this checkout — skipping PR creation.")
        sys.exit(0)

    pr_url = run_full_pipeline(
        repo_full_name=repo_full_name,
        token=token,
        file_path=error_info.file_path,
        fixed_content=result["fixed_file_content"],
        pr_title=result.get("pr_title", "fix: automated bug fix"),
        pr_body=f"**Root cause:** {result.get('root_cause','')}\n\n"
                f"**Fix:** {result.get('fix_explanation','')}\n\n"
                f"_Opened automatically by CodeAutopsy 🩺 after CI failure._",
        base=base_branch,
    )
    print(f"Opened PR: {pr_url}")


if __name__ == "__main__":
    main()
