# KGiit — Product Requirements Document (PRD)

**Version:** 1.1.0  
**Date:** August 7, 2026  
**Authors:** Shaurya Vaid, Aditya Tiwari, Mihir Bagh  
**Status:** Implemented

---

## 1. Problem Statement

### 1.1 The Git Learning Gap

Git is the foundational tool of modern software engineering — yet it remains one of
the most feared parts of a CS curriculum. KIIT University's student population
routinely encounters the following barriers:

- **Fear of destruction:** Destructive commands (`git reset --hard`, `git rebase`,
  `git push --force`) work on the student's *real* filesystem and *real* remote.
  A single mistake can corrupt a semester's worth of work, causing students to avoid
  practicing advanced commands entirely.
- **No safe environment:** Existing tools like GitHub's online tutorials require internet
  access and don't allow students to practice merge conflicts, rebasing, or push/pull
  workflows without touching live repositories.
- **Generic error messages:** When a student types `git checokut main`, git returns
  `git: 'checokut' is not a git command`. This gives no pedagogical value — the student
  doesn't know if they made a typo, used a deprecated command, or misunderstood the
  concept entirely.

### 1.2 The Repository Triage Gap

Open-source repositories — including those maintained by KIIT students and faculty —
frequently accumulate unclassified issues. A maintainer must manually read every issue,
decide if it's a bug or documentation request, estimate its severity, check for
duplicates, and assign it. This is repetitive, time-consuming, and increasingly
untenable as project size grows.

---

## 2. Product Vision

**KGiit** is a dual-engine CLI that closes both gaps simultaneously:

- **Learn Engine:** A 100% offline, isolated Git sandbox where students can run any
  Git command — including destructive ones — without risk. An embedded ML model
  intercepts failures and provides context-aware pedagogical hints.
- **Analyze Engine:** An internet-connected triage pipeline that retrieves live GitHub
  issues and applies NLP classification to automatically assign severity rankings,
  category labels, and duplicate flags.

**Core principle:** No LLM, no cloud API, no subscription. The tool works on day zero
with only Python and Git installed.

---

## 3. Target Users

| User Type | Description | Primary Use Case |
|-----------|-------------|-----------------|
| **CS Student (Beginner)** | Year 1-2, learning Git for the first time | `kgiit learn` — safe practice environment |
| **CS Student (Intermediate)** | Year 2-3, knows basics, learning branching & remotes | `kgiit learn` — branching/merging track |
| **Open-Source Maintainer** | Maintains a public GitHub repo | `kgiit analyze` — issue triage |
| **Teaching Assistant / Instructor** | Demonstrates Git workflows in class | Both modes — `kgiit learn demo` for live demos |

---

## 4. User Stories & Acceptance Criteria

### Epic 1: Offline Git Learning Sandbox

---

#### US-01: Safe Command Practice
> **As a** CS student new to Git,  
> **I want to** practice Git commands in a safe, isolated environment,  
> **So that** I can learn without fear of corrupting my real projects or the host system.

**Acceptance Criteria:**
- [ ] `kgiit learn` launches an isolated sandbox in a temporary directory
- [ ] All Git commands run inside `$TMPDIR/kgiit-sandbox-<uuid>/` — never in the student's home directory
- [ ] `GIT_CONFIG_GLOBAL` is set to a throwaway temp file so no host git config is modified
- [ ] After the session ends, the sandbox directory is fully deleted (via `SandboxSession.purge()`)
- [ ] A student can run `git reset --hard HEAD` in the sandbox with zero risk to actual files

---

#### US-02: Structured Curriculum
> **As a** student,  
> **I want to** follow a structured, progressive curriculum,  
> **So that** I learn Git concepts in the right order and build on each lesson.

**Acceptance Criteria:**
- [ ] Three tracks available: "Git Basics", "Branching & Merging", "Remotes & Collaboration"
- [ ] Lessons within each track are ordered from foundational to advanced
- [ ] Each lesson displays: concept name, step-by-step instructions, and expected command
- [ ] Student can skip a lesson with a keyboard shortcut
- [ ] Student can switch tracks from the main learn menu

---

#### US-03: ML-Powered Error Hints
> **As a** student who typed a wrong Git command,  
> **I want to** receive a specific, context-aware hint explaining *why* my command was wrong,  
> **So that** I learn from my mistake instead of just retrying randomly.

**Acceptance Criteria:**
- [ ] When a command fails verification, the ML classifier runs within 50ms
- [ ] The classifier identifies the mistake type from 12 categories (TYPO, WRONG_FLAG, MISSING_ARG, etc.)
- [ ] A pre-written hint template is shown, filled with the user's typed command and the expected command
- [ ] If ML confidence < 0.45, the deterministic rule-based fallback triggers instead
- [ ] The hint is shown before the student retries the lesson — not after

---

#### US-04: Merge Conflict Practice
> **As a** student learning branching,  
> **I want to** practice resolving a merge conflict in a safe environment,  
> **So that** I understand conflict markers and resolution before encountering one in a real project.

**Acceptance Criteria:**
- [ ] The "Branching & Merging" track includes a lesson with a pre-seeded merge conflict
- [ ] The sandbox pre-creates two branches with conflicting changes before the lesson starts
- [ ] The student must run `git merge` and resolve the conflict manually
- [ ] Verification checks actual repo state (not just exit code 0)
- [ ] After resolution, a ✅ pass message and a "completion certificate" appear

---

#### US-05: GUI Mode for Visual Learners
> **As a** student who learns better visually,  
> **I want to** see branch graphs and commit history rendered in a GUI,  
> **So that** I can understand how branches and commits relate to each other spatially.

**Acceptance Criteria:**
- [ ] `kgiit learn` → option 2 launches an Electron GUI
- [ ] The GUI shows a real-time branch graph and commit log for the sandbox repo
- [ ] The "Universal Git History Viewer" can open any local git repo via a folder picker
- [ ] Git history view works for repos with 500+ commits (via `--max-count=500` cap)
- [ ] GUI communicates with a local FastAPI server exclusively via `127.0.0.1`
- [ ] All FastAPI requests require the `X-Auth-Token` header (CSRF protection)

---

### Epic 2: Live GitHub Issue Triage

---

#### US-06: Automatic Issue Classification
> **As a** repository maintainer,  
> **I want to** automatically classify all open issues by severity and category,  
> **So that** I can focus my attention on the most critical bugs first.

**Acceptance Criteria:**
- [ ] `kgiit analyze --repo <owner/repo>` fetches all open issues via GitHub REST API
- [ ] Each issue is classified with: severity (HIGH/MEDIUM/LOW), label, owner, reason
- [ ] Results are rendered in a Rich terminal table
- [ ] Without a `GITHUB_TOKEN`, the tool works but is subject to 60 req/hr rate limits
- [ ] With `GITHUB_TOKEN` exported, the rate limit increases to 5000 req/hr

---

#### US-07: Duplicate Issue Detection
> **As a** maintainer,  
> **I want to** identify probable duplicate issues automatically,  
> **So that** I can close redundant tickets and consolidate discussion.

**Acceptance Criteria:**
- [ ] Each issue is compared against all others using Jaccard word-overlap similarity
- [ ] Issues with similarity ≥ 0.60 are flagged as `is_duplicate: true, confidence: "high"`
- [ ] Issues with similarity 0.35–0.59 are flagged as `is_duplicate: true, confidence: "medium"`
- [ ] Duplicate information appears in the triage report

---

#### US-08: Priority-Ranked Summary
> **As a** maintainer reviewing a triage report,  
> **I want to** see issues sorted from most to least critical,  
> **So that** I can process them in the right order without manually sorting.

**Acceptance Criteria:**
- [ ] HIGH severity issues always appear before MEDIUM, which appear before LOW
- [ ] Among same-severity issues, `bug/auth` and `bug/payment` labels rank first
- [ ] Among equal-severity and equal-label issues, older issues (lower number) rank higher
- [ ] The triage summary sentence appears at the bottom of the report
- [ ] Summary format: `"<N> HIGH severity issues need attention, mostly in <label>. <M> issue(s) remain unassigned."`

---

## 5. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Learn mode startup time | < 2 seconds from `kgiit learn` to first lesson prompt |
| ML inference time | < 50ms per classification |
| Git log API response time | < 100ms for up to 500 commits |
| Memory footprint (learn mode) | < 5MB heap excluding model |
| Offline operation | Learn mode must function with zero internet access |
| Python compatibility | 3.10, 3.11, 3.12 (tested in CI matrix) |
| OS compatibility | Ubuntu, macOS, Windows (tested in CI matrix) |
| No external runtime deps | Tool ships with pre-trained `model.joblib` — no model download required |

---

## 6. Out of Scope (v1.1.0)

- Multi-user cloud deployment (KGiit is a single-user local tool by design)
- LLM-generated hints (all hints are pre-written templates)
- GitHub write permissions (the analyze engine is read-only)
- Assignment grading or progress tracking across sessions
- Integration with university LMS systems

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| All 91 unit tests passing | ✅ Achieved |
| CI green on 6 matrix combinations | ✅ Achieved |
| ML model accuracy | ≥ 85% (achieved: 87.6%) |
| Flake8 lint errors | 0 |
| SKILL.md contract tests passing | ✅ All 4 skills verified |
| Offline learn mode functional | ✅ No network calls in learn path |
