"""
kgiit.analyze — GitHub issue analyze engine.

This package implements the formal specifications defined in
.agents/skills/*/SKILL.md and is tested against those specs
in tests/test_skill_contract.py.

v1.2.0 additions:
  - action_log: append-only JSONL audit trail for all write-back actions
  - writeback: human-confirmed write-back orchestration (ADLC pattern)
  - GitHubValidationError: HTTP 422 from GitHub
"""

from kgiit.analyze.action_log import log_action, read_log
from kgiit.analyze.formatting import (
    print_banner,
    print_error,
    print_issues_table,
)
from kgiit.analyze.github_client import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubClient,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubValidationError,
)
from kgiit.analyze.report import write_report
from kgiit.analyze.skills import (
    build_analyze_summary,
    classify_issue,
    detect_duplicates,
    rank_priorities,
)

__all__ = [
    "GitHubAPIError",
    "GitHubAuthError",
    "GitHubClient",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
    "GitHubValidationError",
    "build_analyze_summary",
    "classify_issue",
    "detect_duplicates",
    "log_action",
    "print_banner",
    "print_error",
    "print_issues_table",
    "rank_priorities",
    "read_log",
    "write_report",
]
