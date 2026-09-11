# 🩺 CodeAutopsy — AI Bug Fixer

**CodeAutopsy** watches your builds, diagnoses failures with Claude, writes the
fix, and opens a real Pull Request explaining *why* it broke and *how* it was
fixed — no human debugging required.

Built for hackathon judging on **Technical Achievement**: this isn't a mockup.
It clones real repos, calls a real LLM, and pushes real branches/PRs through
the GitHub API.

---

## 1. What it actually does

1. A CI build/test run fails.
2. CodeAutopsy reads the failure log and parses out the error type, file, and
   line number.
3. It pulls the relevant source file from the repo.
4. It sends the error + code to **Claude** and asks for: root cause, a fix,
   the full corrected file, and a PR title/description.
5. It creates a new branch, commits the fix, pushes it, and opens a **Pull
   Request** — with the AI's explanation as the PR description.

Two ways to trigger it:
- **Live demo (Streamlit app)** — paste any error log, watch it diagnose and
  fix it in front of judges, click a button to open the PR.
- **Fully automated (GitHub Actions)** — wire it to your real CI so it fires
  on every failed build with zero human involvement.

---

## 2. Architecture

```
CodeAutopsy/
├── app.py                     # Streamlit demo UI (the thing judges click through)
├── auto_fix.py                 # Headless CLI used by GitHub Actions
├── core/
│   ├── log_analyzer.py         # Parses tracebacks / pytest failures -> ErrorInfo
│   ├── code_context.py         # Locates + reads the buggy file from the repo
│   ├── ai_fixer.py              # Calls Claude, returns structured fix JSON
│   └── github_handler.py       # git clone / branch / commit / push / open PR
├── .github/workflows/
│   └── codeautopsy.yml         # Auto-triggers on CI failure
├── sample_data/                 # A ready-made buggy file + log for a safe demo
├── requirements.txt
├── .env.example
└── .gitignore
```

**Flow diagram**

```
Build fails
   │
   ▼
log_analyzer.py  ──► structured ErrorInfo (type, file, line, message)
   │
   ▼
code_context.py ──► reads the actual buggy file from the repo
   │
   ▼
ai_fixer.py ──► Claude: root cause + fixed code + PR title/body (JSON)
   │
   ▼
github_handler.py ──► new branch → commit → push → Pull Request opened
```

---

## 3. Requirements

- Python 3.10+
- PyCharm (Community or Professional)
- Git + **Git Bash** (comes with Git for Windows)
- A GitHub account + a **Personal Access Token** with `repo` scope
  (Settings → Developer settings → Personal access tokens → Fine-grained or
  classic token)
- An **Anthropic API key** (console.anthropic.com)
- A free **Streamlit Community Cloud** account (share.streamlit.io) for deployment

---

## 4. Build it in PyCharm (step-by-step)

1. **Create the project**
   - PyCharm → `New Project` → name it `CodeAutopsy` → choose a Python
     interpreter (3.10+) → create a **virtual environment**.
2. **Add the files**
   - Recreate the folder structure above inside the project (or copy in the
     files provided with this plan).
3. **Install dependencies**
   - Open the PyCharm terminal (bottom bar) and run:
     ```bash
     pip install -r requirements.txt
     ```
4. **Set your secrets locally**
   - Copy `.env.example` → `.env` and fill in `ANTHROPIC_API_KEY` and
     `GITHUB_TOKEN`. `.env` is already in `.gitignore` so it won't be
     committed.
5. **Run the demo locally**
   ```bash
   streamlit run app.py
   ```
   This opens `http://localhost:8501` in your browser. Click **"Load sample
   error log"** to try it instantly without touching a real repo.
6. **Test against a real repo (optional but recommended for judging)**
   - Push `sample_data/app_under_test.py` to a small throwaway GitHub repo.
   - In the Streamlit sidebar, enter that repo as `owner/repo`, paste the
     matching traceback, click **Analyze & Generate Fix**, review the diff,
     then click **Create Pull Request** — you'll get a real PR link.

---

## 5. Push the project to GitHub using Git Bash

Open **Git Bash** inside (or pointed at) your PyCharm project folder and run:

```bash
# 1. Initialize the repo (skip if PyCharm already did this)
git init

# 2. Stage everything
git add .

# 3. First commit
git commit -m "Initial commit: CodeAutopsy AI bug fixer"

# 4. Create the GitHub repo (via GitHub CLI, if installed)
gh repo create CodeAutopsy --public --source=. --remote=origin

#    --- OR, if you created the repo manually on github.com ---
git remote add origin https://github.com/<your-username>/CodeAutopsy.git

# 5. Push
git branch -M main
git push -u origin main
```

From then on, standard workflow for updates:
```bash
git add .
git commit -m "Describe your change"
git push
```

**Set your secrets on GitHub** (needed for the Actions workflow):
Repo → Settings → Secrets and variables → Actions → New repository secret
- `ANTHROPIC_API_KEY`
- (`GITHUB_TOKEN` is provided automatically by Actions — no need to add it)

---

## 6. Deploy the demo on Streamlit Community Cloud

1. Go to **share.streamlit.io** and sign in with GitHub.
2. Click **"New app"** → select your `CodeAutopsy` repo → branch `main` →
   main file path `app.py`.
3. Under **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   GITHUB_TOKEN = "ghp_..."
   ```
4. Click **Deploy**. You'll get a public URL like
   `https://codeautopsy.streamlit.app` — this is what you demo live to judges.
5. In `app.py`, the sidebar text inputs already default to
   `os.environ.get(...)`, so once secrets are set, judges don't need to type
   any keys in — they just paste a log and click through.

---

## 7. Wire up full automation (optional, big "wow" factor)

The included `.github/workflows/codeautopsy.yml` listens for your existing
**CI** workflow to fail, downloads its logs, and runs `auto_fix.py`
automatically — opening a PR with zero human involvement.

To enable it:
1. Make sure your existing test/build workflow's `name:` field is `CI`
   (or edit `codeautopsy.yml`'s `workflows: ["CI"]` to match your real
   workflow name).
2. Push a commit that intentionally breaks a test.
3. Watch the Actions tab: your CI fails → CodeAutopsy workflow triggers →
   a new PR appears with the fix, all automatically.

This is the strongest live demo for a "Technical Achievement" award: show a
real failing build, then show the bot's PR appearing on its own.

---

## 8. Demo script for judges (2–3 minutes)

1. Open the Streamlit app. Explain the pain: developers spend hours on
   trivial-but-tedious bugs.
2. Click **"Load sample error log"** → **Analyze & Generate Fix**. Narrate:
   "It parsed the traceback, read the actual file from GitHub, and asked
   Claude to diagnose it."
3. Show the diagnosis (root cause) and the diff side-by-side.
4. Click **Create Pull Request** → open the real PR link on GitHub live.
5. (Bonus) Switch tabs to GitHub Actions and show the fully automated
   workflow firing on a real CI failure, no button-click required.

---

## 9. Things to mention as "future work" (judges like a roadmap)

- Support for multi-file fixes (currently: single file per bug)
- Static analysis pre-pass (ruff/flake8) to catch style regressions in the fix
- Confidence-based auto-merge for trivial fixes (e.g. typo-level) vs.
  human review for anything low-confidence
- Support for other languages (JS/TS, Go) via language-aware traceback parsers
- Slack/Discord notification when a PR is opened

---

## 10. License

MIT — free to use, modify, and demo.
