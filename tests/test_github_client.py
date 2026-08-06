import os
import unittest
from unittest.mock import MagicMock, patch
import requests

from kgiit.analyze.github_client import (
    GitHubClient,
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubAuthError,
    GitHubRateLimitError,
)


class TestGitHubClient(unittest.TestCase):

    def setUp(self):
        self.client = GitHubClient(token="test_token_123")

    @patch("requests.Session.get")
    def test_get_issue_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "number": 42,
            "title": "Bug in login flow",
            "body": "Detailed description of the issue.",
            "labels": [{"name": "bug"}, {"name": "priority:high"}],
            "html_url": "https://github.com/octocat/Hello-World/issues/42",
            "created_at": "2026-08-04T12:00:00Z",
            "comments": 5,
        }
        mock_get.return_value = mock_response

        issue = self.client.get_issue("octocat", "Hello-World", 42)

        self.assertEqual(issue["number"], 42)
        self.assertEqual(issue["title"], "Bug in login flow")
        self.assertEqual(issue["body"], "Detailed description of the issue.")
        self.assertEqual(issue["labels"], ["bug", "priority:high"])
        self.assertEqual(issue["url"], "https://github.com/octocat/Hello-World/issues/42")
        self.assertEqual(issue["created_at"], "2026-08-04T12:00:00Z")
        self.assertEqual(issue["comments"], 5)

    @patch("requests.Session.get")
    def test_list_open_issues_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [
            {
                "number": 1,
                "title": "First issue",
                "body": "Body 1",
                "labels": ["enhancement"],
                "html_url": "https://github.com/owner/repo/issues/1",
                "created_at": "2026-08-01T00:00:00Z",
                "comments": 0,
            }
        ]
        mock_get.return_value = mock_response

        issues = self.client.list_open_issues("owner", "repo")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["number"], 1)
        self.assertEqual(issues[0]["labels"], ["enhancement"])

    @patch("requests.Session.get")
    def test_not_found_error_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with self.assertRaises(GitHubNotFoundError):
            self.client.get_issue("nonexistent", "repo", 999)

    @patch("requests.Session.get")
    def test_auth_error_401(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Bad credentials"
        mock_get.return_value = mock_response

        with self.assertRaises(GitHubAuthError):
            self.client.get_issue("owner", "repo", 1)

    @patch("requests.Session.get")
    def test_auth_error_403_with_remaining_quota(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "50"}
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response

        with self.assertRaises(GitHubAuthError):
            self.client.get_issue("owner", "repo", 1)

    @patch("requests.Session.get")
    def test_rate_limit_error_403(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "0"}
        mock_response.text = "API rate limit exceeded"
        mock_get.return_value = mock_response

        with self.assertRaises(GitHubRateLimitError):
            self.client.get_issue("owner", "repo", 1)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "env_secret_token"})
    def test_env_token_loading(self):
        client = GitHubClient()
        self.assertEqual(client.token, "env_secret_token")
        self.assertEqual(client.session.headers["Authorization"], "Bearer env_secret_token")


if __name__ == "__main__":
    unittest.main()
