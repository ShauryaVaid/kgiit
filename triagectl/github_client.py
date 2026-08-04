import os
import requests
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""
    pass


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a repository or issue is not found (404)."""
    pass


class GitHubAuthError(GitHubAPIError):
    """Raised when authentication fails or permissions are missing (401/403)."""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when the GitHub API rate limit is exceeded (403 with X-RateLimit-Remaining: 0)."""
    pass


class GitHubClient:
    """Client for interacting with the GitHub REST API."""

    BASE_URL = "https://api.github.com"
    PLACEHOLDER_SUBSTRINGS = ["your_", "your_github", "<your", "example", "placeholder"]

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize GitHubClient.
        Reads token from parameter, GITHUB_TOKEN, TRIAGE_API_KEY, or API_KEY environment variables.
        Ignores known placeholder values so public GitHub requests succeed unauthenticated.
        """
        raw_token = token or os.getenv("GITHUB_TOKEN") or os.getenv("TRIAGE_API_KEY") or os.getenv("API_KEY")
        
        self.token = None
        if raw_token:
            raw_token = raw_token.strip()
            # Remove any duplicate prefix if user provided "Bearer token" or "token token"
            if raw_token.lower().startswith("bearer "):
                raw_token = raw_token[7:].strip()
            elif raw_token.lower().startswith("token "):
                raw_token = raw_token[6:].strip()

            # Ignore unconfigured placeholder values
            is_placeholder = any(p in raw_token.lower() for p in self.PLACEHOLDER_SUBSTRINGS)
            if not is_placeholder and len(raw_token) > 0:
                self.token = raw_token

        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "triagectl-github-client",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _handle_response(self, response: requests.Response) -> Any:
        """Process API response and raise appropriate custom exceptions."""
        if response.ok:
            return response.json()

        status_code = response.status_code
        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")

        if status_code == 404:
            raise GitHubNotFoundError(f"Resource not found (404): {response.text}")
        elif status_code == 403 and rate_limit_remaining == "0":
            raise GitHubRateLimitError(f"GitHub API rate limit exceeded (403): {response.text}")
        elif status_code in (401, 403):
            raise GitHubAuthError(f"Authentication/Authorization error ({status_code}): {response.text}")
        else:
            raise GitHubAPIError(f"GitHub API request failed with status {status_code}: {response.text}")

    def _normalize_issue(self, raw_issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw GitHub issue dictionary into standardized schema:
        - number (int)
        - title (str)
        - body (str or None)
        - labels (list of str)
        - url (str - html_url)
        - created_at (str)
        - comments (int)
        """
        raw_labels = raw_issue.get("labels", [])
        labels = [
            label["name"] if isinstance(label, dict) and "name" in label else str(label)
            for label in raw_labels
        ]

        return {
            "number": raw_issue.get("number"),
            "title": raw_issue.get("title", ""),
            "body": raw_issue.get("body"),
            "labels": labels,
            "url": raw_issue.get("html_url", raw_issue.get("url", "")),
            "created_at": raw_issue.get("created_at"),
            "comments": raw_issue.get("comments", 0),
        }

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Fetch details for a single issue by owner, repo, and issue_number."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        response = self.session.get(url)
        data = self._handle_response(response)
        return self._normalize_issue(data)

    def list_open_issues(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List all open issues for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": "open"}
        response = self.session.get(url, params=params)
        data = self._handle_response(response)
        return [self._normalize_issue(item) for item in data if isinstance(item, dict)]
