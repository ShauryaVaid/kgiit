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
    """Raised when GitHub rejects a write request as invalid (422)."""


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
        elif status_code == 403 and rate_limit_remaining == "0":
            raise GitHubRateLimitError(
                f"GitHub API rate limit exceeded (403): {response.text}")
        elif status_code in (401, 403):
            raise GitHubAuthError(
                f"Authentication/Authorization error ({status_code}): {response.text}")
        elif status_code == 422:
            raise GitHubValidationError(
                f"GitHub rejected the request as invalid (422): {response.text}")
        else:
            raise GitHubAPIError(
                f"GitHub API request failed with status {status_code}: {response.text}")

    def _guarded_call(self, fn, *args, **kwargs) -> Any:
        """
        Execute a requests call and translate low-level network failures
        (no connection, DNS failure, timeout) into GitHubAPIError so that
        callers only ever need to catch one exception family — including
        when GitHub is simply unreachable, not just when it responds with
        an error status code.
        """
        try:
            response = fn(*args, **kwargs)
        except requests.exceptions.RequestException as exc:
            raise GitHubAPIError(
                f"Network error while contacting GitHub API: {exc}") from exc
        return self._handle_response(response)

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
        data = self._guarded_call(self.session.get, url)
        return self._normalize_issue(data)

    def list_open_issues(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List all open issues for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": "open"}
        data = self._guarded_call(self.session.get, url, params=params)
        return [self._normalize_issue(item)
                for item in data if isinstance(item, dict)]

    def get_authenticated_user(self) -> dict[str, Any]:
        """
        Fetch the identity of whoever GITHUB_TOKEN authenticates as.

        Used to attribute write-back confirmations to a real, verified
        GitHub identity instead of a self-reported name. Requires a token;
        raises GitHubAuthError if none is configured.
        """
        if not self.token:
            raise GitHubAuthError(
                "No GITHUB_TOKEN configured — cannot resolve authenticated identity.")
        url = f"{self.base_url}/user"
        return self._guarded_call(self.session.get, url)

    def add_labels(self, owner: str, repo: str, issue_number: int,
                   labels: list[str]) -> list[str]:
        """
        Add one or more labels to a real GitHub issue via the API.

        This is a WRITE operation — it changes live, third-party-visible
        state and should only ever be called after an explicit human
        confirmation upstream (see kgiit.analyze.writeback). It is
        additive: existing labels on the issue are preserved, GitHub
        simply appends the new ones (and creates any label that doesn't
        already exist on the repo).

        Returns the full, current list of label names now on the issue.
        Raises GitHubAuthError if no token is configured, since writes are
        never permitted unauthenticated.
        """
        if not self.token:
            raise GitHubAuthError(
                "No GITHUB_TOKEN configured — write-back requires an authenticated, "
                "authorized token (repo or public_repo scope).")
        if not labels:
            raise GitHubValidationError(
                "add_labels called with an empty label list — nothing to apply.")

        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels"
        data = self._guarded_call(
            self.session.post, url, json={"labels": labels})
        return [item["name"] if isinstance(item, dict) and "name" in item
                else str(item) for item in data]
