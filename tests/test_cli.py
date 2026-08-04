import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from triagectl.cli import main
from triagectl.github_client import (
    GitHubNotFoundError,
    GitHubAuthError,
    GitHubRateLimitError,
    GitHubAPIError,
)


class TestCLI(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_missing_repo_option(self):
        result = self.runner.invoke(main, ["--all-open"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Missing option '--repo'", result.output)

    def test_mutual_exclusion_issue_and_all_open(self):
        result = self.runner.invoke(main, ["--repo", "owner/repo", "--issue", "42", "--all-open"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Cannot pass both --issue and --all-open", result.output)

    def test_neither_issue_nor_all_open(self):
        result = self.runner.invoke(main, ["--repo", "owner/repo"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Must specify either --issue <number> or --all-open", result.output)

    def test_invalid_repo_format(self):
        result = self.runner.invoke(main, ["--repo", "invalid_repo_name", "--all-open"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Invalid repository format 'invalid_repo_name'", result.output)

    @patch("triagectl.cli.GitHubClient")
    @patch("triagectl.cli.write_report")
    def test_all_open_success(self, mock_write_report, mock_github_client_cls):
        mock_client = MagicMock()
        mock_github_client_cls.return_value = mock_client
        mock_client.list_open_issues.return_value = [
            {
                "number": 1,
                "title": "Issue 1",
                "labels": ["bug"],
                "comments": 2,
                "url": "https://github.com/owner/repo/issues/1",
            }
        ]
        mock_write_report.return_value = "triage-report.md"

        result = self.runner.invoke(main, ["--repo", "owner/repo", "--all-open"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("GitHub Issues", result.output)
        self.assertIn("Report generated successfully at: triage-report.md", result.output)
        mock_write_report.assert_called_once()

    @patch("triagectl.cli.GitHubClient")
    @patch("triagectl.cli.write_report")
    def test_no_report_flag(self, mock_write_report, mock_github_client_cls):
        mock_client = MagicMock()
        mock_github_client_cls.return_value = mock_client
        mock_client.list_open_issues.return_value = [
            {
                "number": 1,
                "title": "Issue 1",
                "labels": [],
                "comments": 0,
                "url": "https://github.com/owner/repo/issues/1",
            }
        ]

        result = self.runner.invoke(main, ["--repo", "owner/repo", "--all-open", "--no-report"])
        self.assertEqual(result.exit_code, 0)
        mock_write_report.assert_not_called()

    @patch("triagectl.cli.GitHubClient")
    def test_not_found_error_handling(self, mock_github_client_cls):
        mock_client = MagicMock()
        mock_github_client_cls.return_value = mock_client
        mock_client.list_open_issues.side_effect = GitHubNotFoundError("Repo does not exist")

        result = self.runner.invoke(main, ["--repo", "owner/nonexistent", "--all-open"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Repository or issue not found", result.output)

    @patch("triagectl.cli.GitHubClient")
    def test_auth_error_handling(self, mock_github_client_cls):
        mock_client = MagicMock()
        mock_github_client_cls.return_value = mock_client
        mock_client.list_open_issues.side_effect = GitHubAuthError("Unauthorized")

        result = self.runner.invoke(main, ["--repo", "owner/repo", "--all-open"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error: Authentication failed (check GITHUB_TOKEN)", result.output)


if __name__ == "__main__":
    unittest.main()
