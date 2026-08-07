# KGiit — Task Breakdown & Sprint Log

This document is the living task breakdown for the KGiit project.
It records what was planned, what was built, and in what order — satisfying the
"task breakdown" submission requirement for the Deploy or Die hackathon.

---

## Sprint 0 — Foundation & Architecture Planning

**Goal:** Define the system architecture, select the tech stack, and set up the repo.

- [x] Define dual-mode architecture (Analyze vs. Learn)
- [x] Select tech stack: Python CLI (Click + Rich), FastAPI, Electron, scikit-learn
- [x] Initialize `pyproject.toml` with correct metadata and dependencies
- [x] Create project skeleton: `kgiit/`, `tests/`, `gui/`, `.agents/`, `.github/`
- [x] Configure `.gitignore` (exclude `.env`, `*.egg-info`, `model.joblib` from lint)
- [x] Write initial `ARCHITECTURE.md` with Mermaid topology diagram
- [x] Set up CI: `.github/workflows/ci.yml` with 6-matrix cross-platform testing

---

## Sprint 1 — Analyze Engine

**Goal:** Implement the live GitHub issue triage pipeline end-to-end.

### Task 1.1 — GitHub API Client
- [x] Implement `kgiit/analyze/github_client.py`
  - [x] Paginated issue fetching via GitHub REST API
  - [x] `GITHUB_TOKEN` env var support for rate limit bypass
  - [x] Handle 403 (rate limited) and 404 (repo not found) gracefully

### Task 1.2 — Skill Specifications (Formal Specs First)
- [x] Write `.agents/skills/issue-triage/SKILL.md` (severity, label, owner, reason schema)
- [x] Write `.agents/skills/duplicate-detector/SKILL.md` (Jaccard similarity schema)
- [x] Write `.agents/skills/priority-ranker/SKILL.md` (ranked list schema)
- [x] Write `.agents/skills/triage-summary/SKILL.md` (plain text output schema)

### Task 1.3 — Skill Implementations
- [x] Implement `classify_issue()` in `kgiit/analyze/skills.py`
- [x] Implement `detect_duplicates()` using Jaccard word overlap
- [x] Implement `rank_priorities()` with 3-tier sort key
- [x] Implement `build_analyze_summary()` per triage-summary spec

### Task 1.4 — Skill Contract Tests
- [x] Write `tests/test_skill_contract.py`
  - [x] Auto-parse SKILL.md JSON schemas
  - [x] Assert classify_issue() returns all declared keys with correct types
  - [x] Assert detect_duplicates() returns correct schema
  - [x] Assert rank_priorities() returns ordered list with correct rank integers
  - [x] Assert build_analyze_summary() returns plain string (no JSON, no markdown)

### Task 1.5 — Output Formatting
- [x] Implement `kgiit/analyze/formatting.py` — Rich terminal table renderer
- [x] Fix column truncation bug on Windows (min_width=15 for Category column)
- [x] Implement `kgiit/analyze/report.py` — markdown report generator

### Task 1.6 — Analyze CLI Entry Point
- [x] Implement `kgiit/analyze/cli.py` with Click command group
- [x] Support `--repo`, `--all-open`, `--limit` flags
- [x] Write `tests/test_formatting.py`, `tests/test_report.py`, `tests/test_github_client.py`

---

## Sprint 2 — Learn Engine Core

**Goal:** Build the offline sandbox and the TUI-based curriculum system.

### Task 2.1 — Sandbox Session
- [x] Implement `kgiit/learn/sandbox.py` → `SandboxSession`
  - [x] Isolated temp directory per session
  - [x] `GIT_CONFIG_GLOBAL` injection to prevent host git config pollution
  - [x] `run_user_command()` — execute git commands in sandbox
  - [x] `get_state()` — inspect staged/unstaged/branch state
  - [x] `purge()` — clean up temp directory on session end
- [x] Write `tests/test_sandbox.py` (9.5KB test suite)

### Task 2.2 — Curriculum Definitions
- [x] Implement `kgiit/learn/curriculum.py` — Track + Lesson dataclasses
  - [x] Track 1: Git Basics (init, status, add, commit)
  - [x] Track 2: Branching & Merging (branch, switch, merge + conflict scenario)
  - [x] Track 3: Remotes & Collaboration (clone, push, pull with offline simulation)
- [x] Define verification functions that check ACTUAL git state (not just exit codes)
- [x] Define fixture states for each lesson (empty, staged, committed, etc.)

### Task 2.3 — TUI Implementation
- [x] Implement `kgiit/learn/tui.py` using Textual framework (17KB)
  - [x] Main menu with track selection
  - [x] Lesson view with command input and output display
  - [x] ML hint panel — shows on failed verification
  - [x] Progress bar across lessons
  - [x] Completion certificate on track finish
  - [x] Headless mode: `kgiit learn --headless`

### Task 2.4 — ML Classifier
- [x] Generate training data: `kgiit/learn/ml/data_gen.py` (247KB CSV)
- [x] Implement training pipeline: `kgiit/learn/ml/train.py`
  - [x] Features: edit_distance, flag_delta, arg_delta, context_has_staged, etc.
  - [x] scikit-learn Random Forest pipeline with StandardScaler
  - [x] Achieved 87.6% accuracy on held-out set
- [x] Implement inference wrapper: `kgiit/learn/ml/classifier.py`
  - [x] Lazy model loading
  - [x] Confidence threshold fallback (0.45)
  - [x] 12 pre-written hint templates
  - [x] Deterministic rule-based fallback (Levenshtein + token analysis)
- [x] Commit trained `model.joblib` to repo
- [x] Write `tests/test_ml_classifier.py` (8KB)

### Task 2.5 — Learn CLI Entry Point
- [x] Implement `kgiit/learn/cli.py` with Click command
  - [x] `kgiit learn` → interactive menu
  - [x] `kgiit learn --headless` → TUI without GUI
  - [x] `kgiit learn demo` → automated demo walkthrough for judges

---

## Sprint 3 — Electron GUI + FastAPI Bridge

**Goal:** Build the visual interface for the Learn mode and secure the local server.

### Task 3.1 — FastAPI Server
- [x] Implement `kgiit/learn/server.py`
  - [x] `GET /api/tracks` — list all available tracks
  - [x] `POST /api/session/start` — create sandbox session
  - [x] `POST /api/session/{id}/execute` — run command in sandbox
  - [x] `GET /api/session/{id}/status` — get current repo state
  - [x] `POST /api/session/{id}/verify` — verify lesson completion + return ML hint
  - [x] `POST /api/session/{id}/lesson/{idx}/setup` — reset to lesson fixture
  - [x] `POST /api/session/{id}/stop` — clean up session
- [x] Implement CSRF protection: randomized `X-Auth-Token` per session
- [x] Use `hmac.compare_digest` for timing-safe token comparison
- [x] Bind server exclusively to `127.0.0.1`

### Task 3.2 — Electron Frontend
- [x] Build `gui/index.html` — main application shell
- [x] Build `gui/renderer.js` — lesson UI, command input, hint display
- [x] Build `gui/preload.js` — contextBridge for IPC
- [x] Build `gui/main.js` — Electron bootstrapper
- [x] Build `gui/styles.css` — cyberpunk-themed UI tokens

### Task 3.3 — Write FastAPI Tests
- [x] Write `tests/test_logs.py`
  - [x] Test missing git binary → `FileNotFoundError` → 500
  - [x] Test subprocess timeout → `TimeoutExpired` → 504
  - [x] Test non-repository path → 400 (missing .git)
  - [x] Test directory traversal attempt → 400

---

## Sprint 4 — Git History Viewer (v1.1.0)

**Goal:** Add a universal Git history viewer to the Electron GUI.

- [x] Implement `GET /api/git/log` endpoint in `server.py`
  - [x] Enforce path canonicalization via `os.path.realpath()`
  - [x] Validate `.git` directory presence before running subprocess
  - [x] Cap output at 500 commits with `--max-count=500`
  - [x] 10-second subprocess timeout
  - [x] Null-byte delimited output parsing for structured commit data
- [x] Add Universal Folder Picker to Electron GUI (native OS dialog)
- [x] Add Git History panel in `gui/renderer.js` — branch graph rendering
- [x] Update `CHANGELOG.md` with v1.1.0 entry
- [x] Merge via PR #1 from `feature/git-log-viewer`

---

## Sprint 5 — Polish, Security & Submission Prep

**Goal:** Harden the codebase, fix all lint errors, and complete submission requirements.

- [x] Run `ruff check --fix` — cleared 204 formatting/import errors
- [x] Run flake8 — 0 remaining errors
- [x] Fix TUI headless mode for CI environments
- [x] Add `kgiit learn demo` — hands-free walkthrough for judges
- [x] Add completion certificate to TUI and GUI
- [x] Write `VERIFICATION.md` — self-audit of all capabilities
- [x] Embed screenshots in `assets/images/`
- [x] Create `AGENTS.md` — agent constitution and behavioral rules
- [x] Create `AGENTS_AND_SKILLS.md` — full skill registry
- [x] Create `PRD.md` — product requirements with user stories
- [x] Fix Python version in `python-app.yml` (3.14 → 3.11)
- [x] Fix version consistency (`pyproject.toml` 1.0.0 → 1.1.0)
- [x] Create git tag `v1.1.0` and GitHub Release
- [x] Expand `ARCHITECTURE.md` with full data model and API contracts

---

## Backlog (Future / Post-Hackathon)

- [ ] Add Playwright E2E tests for the Electron GUI endpoints
- [ ] Add `--output json` flag to `kgiit analyze` for programmatic consumption
- [ ] Add `kgiit learn progress` to persist lesson completion across sessions
- [ ] Add fourth curriculum track: "Advanced Rebase & Cherry-Pick"
- [ ] Package as a standalone binary with PyInstaller for non-Python users
- [ ] Add GitHub Issues write support to auto-label after triage
