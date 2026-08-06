"""
kgiit.analyze — GitHub issue analyze engine.

This package implements the formal specifications defined in
.agents/skills/*/SKILL.md and is tested against those specs
in tests/test_skill_contract.py.
"""

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
    "build_analyze_summary",
    "classify_issue",
    "detect_duplicates",
    "print_banner",
    "print_error",
    "print_issues_table",
    "rank_priorities",
    "write_report",
]
