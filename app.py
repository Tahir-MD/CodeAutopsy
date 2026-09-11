"""
CodeAutopsy - Streamlit Control Panel
=======================================
Live demo UI: paste a build/error log, point at a GitHub repo, watch
Claude diagnose the bug, review the proposed fix, and (optionally)
open a real Pull Request with one click.

Run locally:  streamlit run app.py
"""

import os
import difflib
import streamlit as st

from core.log_analyzer import parse_log
from core.code_context import build_context, read_file_safe
from core.ai_fixer import generate_fix
from core.github_handler import clone_repo, run_full_pipeline

st.set_page_config(page_title="CodeAutopsy", page_icon="🩺", layout="wide")

# ---------- Sidebar: credentials ----------
st.sidebar.title("🩺 CodeAutopsy")
st.sidebar.caption("AI Bug Fixer — from stack trace to Pull Request")

groq_api_key= st.sidebar.text_input(
    "Anthropic API Key", type="password",
    value=os.environ.get("ANTHROPIC_API_KEY", ""),
    help="Used to call Claude for diagnosis + fix generation."
)
github_token = st.sidebar.text_input(
    "GitHub Personal Access Token", type="password",
    value=os.environ.get("GITHUB_TOKEN", ""),
    help="Needs repo scope. Only required if you want to auto-open a PR."
)
repo_full_name = st.sidebar.text_input("Repo (owner/name)", placeholder="octocat/hello-world")
base_branch = st.sidebar.text_input("Base branch", value="main")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**How it works**\n"
    "1. Paste a failing build/test log\n"
    "2. CodeAutopsy locates the broken file in your repo\n"
    "3. Claude explains the bug and writes a fix\n"
    "4. Review the diff, then open a real PR"
)

st.title("CodeAutopsy 🩺 — AI Bug Fixer")
st.caption("Paste an error log below. CodeAutopsy will diagnose it, fix it, and can open a PR automatically.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Paste the failing build/test log")
    default_log = ""
    sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_error_log.txt")
    if os.path.exists(sample_path) and st.button("Load sample error log"):
        with open(sample_path) as f:
            default_log = f.read()
    log_text = st.text_area("Error log / traceback", value=default_log, height=300,
                             placeholder="Traceback (most recent call last):\n  File ...")

    analyze_clicked = st.button("🔍 Analyze & Generate Fix", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Diagnosis")
    diagnosis_box = st.container()

# ---------- Session state ----------
if "fix_result" not in st.session_state:
    st.session_state.fix_result = None
if "error_info" not in st.session_state:
    st.session_state.error_info = None

# ---------- Analysis pipeline ----------
if analyze_clicked:
    if not log_text.strip():
        st.warning("Paste an error log first.")
    elif not groq_api_key:
        st.warning("Add your Anthropic API key in the sidebar.")
    else:
        with st.spinner("Parsing traceback..."):
            error_info = parse_log(log_text)
            st.session_state.error_info = error_info

        context = {"full_file": None, "snippet": None, "found": False}
        if repo_full_name and github_token:
            with st.spinner(f"Cloning {repo_full_name} to read source..."):
                try:
                    repo_path = clone_repo(repo_full_name, github_token)
                    context = build_context(repo_path, error_info)
                except Exception as e:
                    st.error(f"Could not clone repo: {e}")

        with st.spinner("Asking Claude to diagnose and fix the bug..."):
            try:
                result = generate_fix(error_info, context, api_key=groq_api_key)
                result["_file_path"] = error_info.file_path
                result["_original_content"] = context.get("full_file")
                st.session_state.fix_result = result
            except Exception as e:
                st.error(f"AI fix generation failed: {e}")

# ---------- Show diagnosis ----------
with diagnosis_box:
    ei = st.session_state.error_info
    if ei:
        st.markdown(f"**Error type:** `{ei.error_type}`")
        st.markdown(f"**Message:** {ei.message}")
        st.markdown(f"**File:** `{ei.file_path or 'unknown'}`  |  **Line:** {ei.line_number or '?'}")

    fr = st.session_state.fix_result
    if fr:
        st.success(f"Confidence: **{fr.get('confidence', 'unknown').upper()}**")
        st.markdown("**Root cause:**")
        st.write(fr.get("root_cause", ""))
        st.markdown("**Proposed fix:**")
        st.write(fr.get("fix_explanation", ""))

# ---------- Diff + PR ----------
if st.session_state.fix_result:
    st.subheader("3. Review the fix")
    fr = st.session_state.fix_result
    original = fr.get("_original_content") or ""
    fixed = fr.get("fixed_file_content") or ""

    if original:
        diff = difflib.unified_diff(
            original.splitlines(), fixed.splitlines(),
            fromfile="original", tofile="fixed", lineterm=""
        )
        diff_text = "\n".join(diff) or "(no textual diff detected)"
        st.code(diff_text, language="diff")
    else:
        st.info("Repo not connected — showing AI's proposed file content only.")
        st.code(fixed, language="python")

    st.subheader("4. Open a Pull Request")
    pr_title = st.text_input("PR title", value=fr.get("pr_title", "fix: automated bug fix"))
    pr_body = st.text_area(
        "PR description",
        value=f"**Root cause:** {fr.get('root_cause','')}\n\n"
              f"**Fix:** {fr.get('fix_explanation','')}\n\n"
              f"_Opened automatically by CodeAutopsy 🩺_",
        height=150,
    )

    if st.button("🚀 Create Pull Request", type="primary"):
        if not (github_token and repo_full_name and fr.get("_file_path")):
            st.error("Repo, GitHub token, and a located file path are all required to open a PR.")
        else:
            with st.spinner("Pushing branch and opening PR..."):
                try:
                    pr_url = run_full_pipeline(
                        repo_full_name=repo_full_name,
                        token=github_token,
                        file_path=fr["_file_path"],
                        fixed_content=fixed,
                        pr_title=pr_title,
                        pr_body=pr_body,
                        base=base_branch,
                    )
                    st.success("Pull request opened!")
                    st.markdown(f"🔗 [View the PR]({pr_url})")
                except Exception as e:
                    st.error(f"Failed to open PR: {e}")
