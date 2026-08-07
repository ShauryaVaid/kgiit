# KGiit Agent Constitution

This file defines the rules, constraints, and behavioral guidelines for any AI agent
working on the KGiit codebase. It applies to all agentic workflows — Cline, Roo Code,
BMAD, Spec Kit, or any other tool-calling agent operating in this repository.

---

## Project Identity

**Name:** KGiit  
**Version:** 1.1.0  
**Purpose:** A dual-engine CLI tool for Git education (offline sandbox) and live GitHub
repository triage (NLP-powered issue analysis).  
**Primary Language:** Python 3.10+  
**Secondary:** JavaScript (Electron GUI), YAML (CI), TOML (packaging)

---

## Agent Role & Scope

The agent's role in this project is:

1. **Implement features** described in PRD.md and the task breakdown (TASKS.md).
2. **Maintain and extend** the test suite in `tests/` — every new function must have tests.
3. **Enforce the skill contract** between `.agents/skills/*/SKILL.md` specs and
   their Python implementations in `kgiit/analyze/skills.py`.
4. **Keep CI green.** Never commit code that breaks any workflow in `.github/workflows/`.
5. **Document as you build.** Update `ARCHITECTURE.md`, `CHANGELOG.md`, and
   `AGENTS_AND_SKILLS.md` as features land.

---

## Absolute Rules (Never Violate)

- **No secrets committed.** Never write API keys, tokens, passwords, or personal data
  into any file. Use `.env` (gitignored) and `.env.example` for key references.
- **No `0.0.0.0` bindings.** The FastAPI server MUST bind to `127.0.0.1` only.
  Exposing it on all interfaces is a security violation.
- **No blind auto-generation.** Every generated block of code must be reviewed by a
  human before commit. The agent proposes; the human approves.
- **No single giant commits.** Commits must be atomic: one logical change per commit.
  If an implementation spans multiple concerns, split it into multiple commits.
- **No breaking the offline guarantee.** The `kgiit learn` mode must remain 100%
  offline. Do not add network calls, LLM API calls, or external service dependencies
  to anything under `kgiit/learn/`.
- **No unchecked subprocess calls.** Any `subprocess.run()` inside `kgiit/learn/`
  must use explicit argument lists (no `shell=True`), a timeout, and path validation.

---

## Coding Standards

### Python
- **Style:** PEP 8, max line length 110 characters (enforced by flake8 in CI).
- **Type hints:** All public functions must have full type annotations.
- **Docstrings:** All modules and public functions must have docstrings.
- **Error handling:** Catch specific exceptions. Never use bare `except:`.
- **Imports:** Standard library → third-party → local, each group separated by a blank line.
- **No deprecated APIs:** Use `git switch` not `git checkout` for branch operations in
  curriculum examples.

### Tests
- **Framework:** pytest only. No unittest discovery workarounds.
- **Coverage target:** ≥ 80% for any new module added.
- **Naming:** `test_<module>_<what_it_tests>` pattern.
- **Mocking:** Use `unittest.mock` for external API calls. Never make live GitHub API
  calls in tests.
- **Skill contract tests:** After any change to a SKILL.md, run
  `pytest tests/test_skill_contract.py -v` to verify the implementation still matches.

### JavaScript (Electron GUI)
- Use `const` and `let`. Never `var`.
- IPC calls use `contextBridge` in `preload.js` — do not call `ipcRenderer` directly
  from `renderer.js`.
- All fetch calls to the FastAPI backend must include the `X-Auth-Token` header.

---

## Commit Message Format

Use Conventional Commits:

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `ci`, `chore`, `security`, `perf`

Scopes: `learn`, `analyze`, `cli`, `gui`, `ml`, `sandbox`, `ci`, `deps`

Examples:
- `feat(learn): add merge conflict resolution lesson to branching track`
- `fix(server): enforce path canonicalization before subprocess call`
- `test(ml): add edge cases for WRONG_CONTEXT_STATE label classification`
- `security(server): replace == with hmac.compare_digest for token check`

---

## Branch Strategy

- `main` — production-ready, CI must be green
- `feature/<name>` — new features, branched from `main`, merged via PR
- `fix/<name>` — bug fixes
- `chore/<name>` — maintenance (deps, docs, config)

**PRs required for all changes to `main`.** Direct pushes to `main` are only allowed
for emergency hotfixes with justification in the commit message.

---

## Skill Integration Contract

When implementing a new skill:

1. Write the formal specification in `.agents/skills/<skill-name>/SKILL.md` first.
2. Include a JSON schema block in the `## Output Requirement` section.
3. Implement the Python function in `kgiit/analyze/skills.py`.
4. Add contract tests in `tests/test_skill_contract.py` that:
   - Verify the SKILL.md file exists
   - Parse its JSON schema keys
   - Assert the implementation returns all declared keys with correct types
5. Update `AGENTS_AND_SKILLS.md` with the new skill.

The contract test suite is non-negotiable. Schema drift between spec and implementation
is caught at CI time, not at judge time.

---

## ML Model Governance

- The model at `kgiit/learn/ml/model.joblib` is the authoritative trained artifact.
- To retrain: `python -m kgiit.learn.ml.train` — this reads `training_data.csv`.
- **Do not manually edit `model.joblib`.** It is a binary artifact; all changes go
  through the training pipeline.
- The confidence threshold (currently 0.45) may be tuned but must be documented in
  `CHANGELOG.md` with justification.
- Rule-based fallback (`_rule_based_classify`) must always remain as the safety net.

---

## What the Agent Must NOT Do

- Do not add Playwright tests that require a browser binary not available in CI.
  Use `httpx` + `pytest` for API-level E2E testing instead.
- Do not install packages not already in `pyproject.toml` without updating the
  dependency list and documenting the reason.
- Do not modify `.github/workflows/ci.yml` matrix to reduce coverage without
  explicit approval (e.g., removing a platform OS).
- Do not add any telemetry, analytics, or data collection of any kind.
- Do not hallucinate test results. If a test is flaky, mark it with
  `@pytest.mark.skip(reason="...")` and open an issue.

---

## Definition of Done

A feature is complete when:

- [ ] Code is implemented and passes all linting (`flake8 kgiit/`)
- [ ] New tests written and passing (`pytest tests/ -v`)
- [ ] SKILL.md updated if a new skill was added
- [ ] `test_skill_contract.py` passes for any new skill
- [ ] `CHANGELOG.md` updated with entry under the current version
- [ ] `AGENTS_AND_SKILLS.md` updated if a new agent/skill was added
- [ ] CI is green on all matrix combinations
- [ ] Committed with a conventional commit message
