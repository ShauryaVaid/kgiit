"""
triagectl - CLI tool for automated triage workflows.
"""

from triagectl.github_client import (
    GitHubClient,
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubAuthError,
    GitHubRateLimitError,
)
from triagectl.formatting import (
    print_banner,
    print_issues_table,
    print_error,
)
from triagectl.report import (
    write_report,
)

__version__ = "0.1.0"

__all__ = [
    "GitHubClient",
    "GitHubAPIError",
    "GitHubNotFoundError",
    "GitHubAuthError",
    "GitHubRateLimitError",
    "print_banner",
    "print_issues_table",
    "print_error",
    "write_report",
]
