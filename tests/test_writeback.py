import os
import tempfile
import unittest
from unittest.mock import MagicMock

from kgiit.analyze.action_log import read_log
from kgiit.analyze.github_client import GitHubAPIError, GitHubAuthError
from kgiit.analyze.writeback import (
    apply_suggestion,
    build_suggestion_labels,
    decline_suggestion,
    resolve_identity,
)


class TestBuildSuggestionLabels(unittest.TestCase):

    def test_full_classification_produces_two_labels(self):
        labels = build_suggestion_labels(
            {"label": "bug/auth", "severity": "HIGH"})
        self.assertEqual(labels, ["bug/auth", "priority:high"])

    def test_uncategorized_label_is_dropped(self):
        labels = build_suggestion_labels(
            {"label": "uncategorized", "severity": "LOW"})
        self.assertEqual(labels, ["priority:low"])

    def test_no_severity_no_label_is_empty(self):
        self.assertEqual(build_suggestion_labels({}), [])


class TestResolveIdentity(unittest.TestCase):

    def test_prefers_verified_github_login(self):
        client = MagicMock()
        client.get_authenticated_user.return_value = {"login": "octocat"}
        identity = resolve_identity(client, fallback="ignored")
        self.assertEqual(identity, "github:octocat")

    def test_falls_back_to_explicit_name_when_auth_fails(self):
        client = MagicMock()
        client.get_authenticated_user.side_effect = GitHubAuthError("no token")
        identity = resolve_identity(client, fallback="Shaurya")
        self.assertEqual(identity, "Shaurya")

    def test_falls_back_to_os_user_when_nothing_else_available(self):
        client = MagicMock()
        client.get_authenticated_user.side_effect = GitHubAuthError("no token")
        identity = resolve_identity(client, fallback=None)
        self.assertTrue(identity.startswith("os:") or identity == "unknown")


class TestApplySuggestion(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self._tmpdir.name, "actions.jsonl")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_successful_apply_calls_client_and_logs_applied(self):
        client = MagicMock()
        client.add_labels.return_value = ["bug", "priority:high"]

        result = apply_suggestion(
            client,
            owner="octocat",
            repo="Hello-World",
            issue_number=42,
            classification={"label": "bug", "severity": "HIGH"},
            confirmed_by="github:octocat",
            log_path=self.log_path,
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["applied"])
        client.add_labels.assert_called_once_with(
            "octocat", "Hello-World", 42, ["bug", "priority:high"])

        entries = read_log(self.log_path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "applied")
        self.assertEqual(entries[0]["confirmed_by"], "github:octocat")
        self.assertEqual(entries[0]["issue_number"], 42)

    def test_github_write_failure_is_caught_and_logged_not_raised(self):
        client = MagicMock()
        client.add_labels.side_effect = GitHubAPIError("403 Forbidden")

        result = apply_suggestion(
            client,
            owner="octocat",
            repo="Hello-World",
            issue_number=42,
            classification={"label": "bug", "severity": "HIGH"},
            confirmed_by="github:octocat",
            log_path=self.log_path,
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["applied"])
        self.assertIn("403 Forbidden", result["error"])

        entries = read_log(self.log_path)
        self.assertEqual(entries[0]["status"], "failed")
        self.assertIn("403 Forbidden", entries[0]["error"])

    def test_unexpected_exception_does_not_propagate(self):
        client = MagicMock()
        client.add_labels.side_effect = RuntimeError("something weird")

        # Must not raise.
        result = apply_suggestion(
            client,
            owner="octocat",
            repo="Hello-World",
            issue_number=42,
            classification={"label": "bug", "severity": "HIGH"},
            confirmed_by="github:octocat",
            log_path=self.log_path,
        )
        self.assertFalse(result["ok"])
        entries = read_log(self.log_path)
        self.assertEqual(entries[0]["status"], "failed")

    def test_no_actionable_label_is_skipped_without_calling_github(self):
        client = MagicMock()
        result = apply_suggestion(
            client,
            owner="octocat",
            repo="Hello-World",
            issue_number=42,
            classification={},
            confirmed_by="github:octocat",
            log_path=self.log_path,
        )
        self.assertFalse(result["ok"])
        client.add_labels.assert_not_called()


class TestDeclineSuggestion(unittest.TestCase):

    def test_decline_never_calls_github_and_logs_declined(self):
        with tempfile.TemporaryDirectory() as d:
            log_path = os.path.join(d, "actions.jsonl")
            result = decline_suggestion(
                owner="octocat",
                repo="Hello-World",
                issue_number=42,
                classification={"label": "bug", "severity": "HIGH"},
                confirmed_by="github:octocat",
                log_path=log_path,
            )
            self.assertFalse(result["ok"])
            entries = read_log(log_path)
            self.assertEqual(entries[0]["status"], "declined")


if __name__ == "__main__":
    unittest.main()
