# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
