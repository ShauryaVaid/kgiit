# Build & Run Guide — KGiit v1.1.0

> **For hackathon judges:** This document is a complete, step-by-step guide to set up, run, and validate every part of KGiit in under 5 minutes. Every command is copy-paste ready.

---

## Prerequisites

| Tool | Minimum Version | Check Command | Download |
|------|----------------|---------------|----------|
| Python | 3.10+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| Git | Any modern | `git --version` | [git-scm.com](https://git-scm.com/) |
| Node.js | 18 LTS+ | `node --version` | [nodejs.org](https://nodejs.org/) (for GUI & E2E tests only) |

> [!NOTE]
> Node.js is **only required** for the Electron GUI and Playwright E2E tests. The core CLI and all Python tests work without it.

---

## ⚡ One-Command Setup (Recommended)

Clone and install everything in one go:

```bash
git clone https://github.com/ShauryaVaid/kgiit.git
cd kgiit
pip install -e ".[dev]"
git config --global user.email "judge@test.com"
git config --global user.name "Judge"
git config --global init.defaultBranch main
kgiit --help
```

If you see the KGiit help menu — **you're ready to go.**

---

## Step-by-Step Setup

### Step 1 — Clone the Repository

```bash
git clone https://github.com/ShauryaVaid/kgiit.git
cd kgiit
```

### Step 2 — Install the Python Package

This installs `kgiit` as a global binary and all its dependencies:

```bash
pip install -e ".[dev]"
```

> [!TIP]
> Using a virtual environment is cleaner but not required:
> ```bash
> python -m venv .venv
> # Windows:
> .venv\Scripts\activate
> # macOS / Linux:
> source .venv/bin/activate
> pip install -e ".[dev]"
> ```

### Step 3 — Configure Git (required for sandbox tests)

```bash
git config --global user.email "judge@test.com"
git config --global user.name "Judge"
git config --global init.defaultBranch main
```

### Step 4 — Verify the CLI Works

```bash
kgiit --help
```

Expected output:
```
Usage: kgiit [OPTIONS] COMMAND [ARGS]...

  KGiit — Two doors. One CLI.
  ...
```

---

## 🚀 Running the App

### Mode 1: Interactive Main Menu (recommended for judges)

```bash
kgiit
```

Use **arrow keys** to navigate. Select **Learn Mode** or **Analyze Mode**. Press `q` or type `/bye` to exit.

---

### Mode 2: Learn Mode — Offline Git Sandbox (CLI/TUI)

```bash
kgiit learn --headless
```

Launches a terminal-based interactive Git tutor. No internet required. Type Git commands as prompted by each lesson.

---

### Mode 3: Learn Mode — Electron GUI

> Requires Node.js

```bash
# Install GUI dependencies (one-time)
cd gui
npm install
cd ..

# Launch: this starts the FastAPI bridge + opens the Electron window
kgiit learn
# → Select option 2 "Launch GUI" from the menu
```

The GUI opens at `http://127.0.0.1:8765` internally and shows:
- Live lesson progress
- Branch graph & commit history viewer
- ML-powered error hints when you type a wrong Git command

---

### Mode 4: Analyze Mode — Live GitHub Issue Triage

```bash
# Without a token (60 req/hr rate limit — fine for demo):
kgiit analyze --repo torvalds/linux

# With a GitHub token (5000 req/hr):
export GITHUB_TOKEN=your_token_here
kgiit analyze --repo torvalds/linux
```

This fetches live issues, runs NLP classification, and prints a ranked triage table with severity (HIGH / MEDIUM / LOW), category labels, and duplicate detection.

---

## ✅ Running the Test Suite

### Python Unit + Integration Tests (87 tests)

```bash
pytest tests/ -v
```

Expected: **87 passed** in ~10–15 seconds.

### Run with Coverage Report

```bash
pytest tests/ --cov=kgiit --cov-report=term-missing
```

### Run Specific Test Groups

```bash
# Skill contract tests (validates all 4 SKILL.md contracts)
pytest tests/test_skill_contract.py -v

# ML classifier tests
pytest tests/test_ml_classifier.py -v

# Sandbox isolation tests
pytest tests/test_sandbox.py -v

# FastAPI server tests
pytest tests/test_server.py -v
```

---

## 🎭 Running Playwright E2E Tests

> Requires Node.js

### One-time setup

```bash
npm install
npx playwright install chromium
```

### Run all 22 E2E tests

```bash
npx playwright test
```

Expected: **22 passed** in ~25 seconds.

The test suite automatically:
1. Starts the FastAPI server on `http://127.0.0.1:8765`
2. Runs API-level tests (session lifecycle, error handling, security)
3. Runs browser-level tests (Swagger UI, in-browser fetch, ML hints)
4. Stops the server when done

### View the HTML Report

```bash
npx playwright show-report
```

Opens a browser with a full pass/fail report for every test.

### Run in Headed Mode (watch the browser)

```bash
npx playwright test --headed
```

---

## 🔍 Running the Linter

```bash
pip install flake8
flake8 kgiit/ --max-line-length=110 --extend-ignore=E203,W503,E501
```

Expected: **0 errors, 0 warnings.**

---

## 📁 Project Structure at a Glance

```
kgiit/
├── kgiit/                  # Core Python package
│   ├── cli.py              # Main CLI entrypoint (kgiit command)
│   ├── analyze/            # NLP GitHub issue triage engine
│   ├── learn/              # Offline Git sandbox + FastAPI bridge
│   │   ├── server.py       # FastAPI server (port 8765)
│   │   ├── sandbox.py      # Isolated git sandbox (temp dir)
│   │   ├── curriculum.py   # 3 tracks, 9 lessons
│   │   └── ml/
│   │       ├── model.joblib        # Pre-trained Random Forest
│   │       └── ml_classifier.py   # Inference engine
│   └── skills/             # 4 registered agent skills
├── gui/                    # Electron GUI
│   ├── main.js             # Electron bootstrapper
│   └── index.html          # Frontend
├── tests/                  # Test suite (87 Python + 22 E2E)
│   ├── e2e/                # Playwright E2E specs
│   └── test_*.py           # Pytest unit/integration tests
├── .github/workflows/      # CI/CD (ci.yml + python-app.yml)
├── ARCHITECTURE.md         # Full system architecture
├── AGENTS.md               # Agent constitution / rules
├── AGENTS_AND_SKILLS.md    # 2 agents + 4 skills registry
├── PRD.md                  # Product requirements + user stories
├── pyproject.toml          # Package definition + dependencies
└── playwright.config.js    # E2E test configuration
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `kgiit: command not found` | Re-run `pip install -e ".[dev]"` in the repo root |
| `npm: command not found` | Install Node.js LTS from [nodejs.org](https://nodejs.org/), restart terminal |
| Playwright `browser not found` | Run `npx playwright install chromium` |
| `git: command not found` in sandbox tests | Install Git and ensure it's in your PATH |
| Port 8765 already in use | Kill the existing process: `lsof -ti:8765 \| xargs kill` (Linux/Mac) or `netstat -ano \| findstr 8765` then `taskkill /PID <id> /F` (Windows) |
| `ModuleNotFoundError` | Ensure you're in the right venv and ran `pip install -e ".[dev]"` |
| Tests fail with git identity error | Run the 3 `git config --global` commands in Step 3 |

---

## 🧪 Full Validation Checklist (for judges)

Run these in order to validate everything:

```bash
# 1. CLI works
kgiit --help

# 2. Python tests pass
pytest tests/ -v

# 3. Linter clean
flake8 kgiit/ --max-line-length=110 --extend-ignore=E203,W503,E501

# 4. E2E tests pass (requires Node.js)
npm install && npx playwright install chromium && npx playwright test

# 5. App launches
kgiit
```

All steps should complete with ✅ green output.

---

<div align="center">
  <b>KGiit v1.1.0</b> &mdash; Built for the <i>Deploy or Die: HowToAlgo × GDG on Campus KIIT Hackathon</i><br/>
  <i>Authored by Shaurya Vaid · Contributors: Aditya Tiwari and Mihir Bagh</i>
</div>
