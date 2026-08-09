from __future__ import annotations

import os
from typing import Any

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a repository or issue is not found (404)."""


class GitHubAuthError(GitHubAPIError):
    """Raised when authentication fails or permissions are missing (401/403)."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when the GitHub API rate limit is exceeded (403 with X-RateLimit-Remaining: 0)."""


class GitHubValidationError(GitHubAPIError):
    """Raised when the GitHub API returns 422 Unprocessable Entity.

    Common causes:
      - Applying a label that doesn't exist in the repository.
      - A malformed request body.
    The error message will include GitHub's validation details.
    """


class GitHubClient:
    """Client for interacting with the GitHub REST API."""

    BASE_URL = "https://api.github.com"
    PLACEHOLDER_SUBSTRINGS = [
        "your_",
        "your_github",
        "<your",
        "example",
        "placeholder"]

    def __init__(self, token: str | None = None, base_url: str | None = None):
        """
        Initialize GitHubClient.
        Reads token from parameter, GITHUB_TOKEN, TRIAGE_API_KEY, or API_KEY environment variables.
        Ignores known placeholder values so public GitHub requests succeed unauthenticated.
        """
        raw_token = token or os.getenv("GITHUB_TOKEN") or os.getenv(
            "TRIAGE_API_KEY") or os.getenv("API_KEY")

        self.token = None
        if raw_token:
            raw_token = raw_token.strip()
            # Remove any duplicate prefix if user provided "Bearer token" or
            # "token token"
            if raw_token.lower().startswith("bearer "):
                raw_token = raw_token[7:].strip()
            elif raw_token.lower().startswith("token "):
                raw_token = raw_token[6:].strip()

            # Ignore unconfigured placeholder values
            is_placeholder = any(p in raw_token.lower()
                                 for p in self.PLACEHOLDER_SUBSTRINGS)
            if not is_placeholder and len(raw_token) > 0:
                self.token = raw_token

        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "kgiit-github-client/1.0.0",
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
            raise GitHubNotFoundError(
                f"Resource not found (404): {response.text}")
        elif status_code == 422:
            raise GitHubValidationError(
                f"Validation failed (422): {response.text}\n"
                "Tip: the label may not exist in this repository. "
                "Create it first in GitHub Settings > Labels.")
        elif status_code == 403 and rate_limit_remaining == "0":
            raise GitHubRateLimitError(
                f"GitHub API rate limit exceeded (403): {response.text}")
        elif status_code in (401, 403):
            raise GitHubAuthError(
                f"Authentication/Authorization error ({status_code}): {response.text}")
        else:
            raise GitHubAPIError(
                f"GitHub API request failed with status {status_code}: {response.text}")

    def _normalize_issue(self, raw_issue: dict[str, Any]) -> dict[str, Any]:
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

    def get_issue(self, owner: str, repo: str,
                  issue_number: int) -> dict[str, Any]:
        """Fetch details for a single issue by owner, repo, and issue_number."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        response = self._guarded_call(self.session.get, url)
        data = self._handle_response(response)
        return self._normalize_issue(data)

    def list_open_issues(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List all open issues for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": "open"}
        response = self._guarded_call(self.session.get, url, params=params)
        data = self._handle_response(response)
        return [self._normalize_issue(item)
                for item in data if isinstance(item, dict)]

    def add_labels(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
    ) -> dict[str, Any]:
        """
        Add labels to an existing GitHub issue (additive — never removes existing labels).

        Requires a GITHUB_TOKEN with at least 'public_repo' scope for public
        repositories, or 'repo' scope for private repositories.

        Args:
            owner: Repository owner login.
            repo: Repository name.
            issue_number: Target issue number.
            labels: List of label name strings to apply.

        Returns:
            The raw GitHub API response dict.

        Raises:
            GitHubAuthError: If the token lacks write permissions.
            GitHubNotFoundError: If the issue doesn't exist.
            GitHubValidationError: If a label name doesn't exist in the repo.
            GitHubAPIError: For any other API failure.
        """
        if not labels:
            return {"labels": []}

        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels"
        payload = {"labels": labels}
        response = self._guarded_call(self.session.post, url, json=payload)
        return self._handle_response(response)

    def get_authenticated_user(self) -> dict[str, Any]:
        """
        Return the GitHub user that the configured token authenticates as.

        Used by writeback.resolve_identity() to obtain a verified GitHub
        login rather than relying on a self-reported --confirmed-by value.

        Returns:
            Dict with at least 'login' and 'name' keys.

        Raises:
            GitHubAuthError: If the token is invalid or missing.
            GitHubAPIError: For any other API failure.
        """
        url = f"{self.base_url}/user"
        response = self._guarded_call(self.session.get, url)
        return self._handle_response(response)

    def _guarded_call(self, method, url: str, **kwargs) -> requests.Response:
        """
        Wrap a requests call to convert all network-level errors into
        GitHubAPIError so callers never see an unhandled ConnectionError,
        Timeout, or similar low-level exception.

        Args:
            method: A bound requests.Session method (e.g. self.session.get).
            url: The full URL to call.
            **kwargs: Additional arguments passed to the method.

        Returns:
            requests.Response — always; never raises a requests exception.

        Raises:
            GitHubAPIError: For any network, DNS, or timeout failure.
        """
        try:
            return method(url, timeout=15, **kwargs)
        except requests.exceptions.Timeout:
            raise GitHubAPIError(
                f"Request timed out after 15 seconds: {url}\n"
                "Check your internet connection and try again."
            )
        except requests.exceptions.ConnectionError as exc:
            raise GitHubAPIError(
                f"Could not connect to GitHub API: {exc}\n"
                "Check your internet connection. "
                "GitHub status: https://www.githubstatus.com/"
            )
        except requests.exceptions.RequestException as exc:
            raise GitHubAPIError(f"Network error: {exc}")
