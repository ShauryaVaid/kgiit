# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-08-09

### Added (Round 2 — Confirmed Write-Back / HowToAlgo ADLC)
- **`kgiit analyze --apply`**: Confirmed write-back — after analysis, a human
  explicitly approves the AI suggestion before it's applied to the real GitHub issue.
  No bypass flag exists; the prompt is mandatory. Scoped to `--issue` only (not
  `--all-open`) to keep the blast radius of any one confirmation to a single issue.
- **`kgiit log`**: New top-level command to view the local write-back audit trail
  as a Rich table (newest-first). Fully offline — works even when GitHub is unreachable.
- **`action_log.py`**: Append-only JSONL audit log recording who confirmed, what was
  suggested, what GitHub returned, and when — for every write-back attempt
  (applied, declined, failed, skipped). Pure file I/O, no GitHub dependency.
- **`writeback.py`**: Confirmed write-back orchestration seam. Contains zero UI code
  by design: fully unit-testable, reusable from the Electron GUI, and a single
  auditable place where "apply a suggestion" is defined.
- **`GitHubValidationError`**: New exception for HTTP 422 responses.
- **`_guarded_call()`**: Network error guard on all GitHub client calls — dead
  network / DNS failure / timeout → `GitHubAPIError`, never an unhandled traceback.
- **`add_labels()` + `get_authenticated_user()`**: New write methods on `GitHubClient`.
  Writes are additive (POST /labels), never destructive.
- **`--dual-approval`**: Optional stretch mode requiring two different confirmers
  before a write is sent.
- **TUI menu options 3 & 4**: Write-back and audit log accessible from the interactive
  Rich menu, not just CLI flags.
- **30 new tests** covering the full decline→confirm judge verification flow,
  graceful failure (no traceback), and all new modules. All 139 tests pass.

## [1.1.0] - 2026-08-07

### Added
- **Git History Viewer (GUI)**: Added a rich, searchable git log panel to the Electron GUI that renders branching graphs and commit history.
- **`GET /api/git/log` Endpoint**: Built a highly secure FastAPI endpoint for fetching repository git history. It enforces path canonicalization, repository validation, and timeouts to protect against symlink traversal and DoS.
- **CSRF Protection**: The FastAPI backend now enforces a randomized `X-Auth-Token` required on all requests, successfully blocking unauthorized browser access on localhost.
- **Universal Folder Picker**: Replaced restrictive sandbox paths with a native OS folder picker, allowing users to view git history for any valid local repository on their system.
- **Comprehensive Endpoint Tests**: Added `tests/test_logs.py` to assert the backend safely handles missing binaries (`FileNotFoundError`), timeouts (`TimeoutExpired`), non-repositories, and directory traversals.
- **Automated CI (GitHub Actions)**: Integrated `python-app.yml` for automated testing on every push/PR.

### Fixed
- **Table Truncation**: Fixed terminal truncation bug where the "Category" column in `kgiit analyze` was cutting off labels on Windows. Column now respects a `min_width=15` boundary.
