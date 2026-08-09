import json
import unittest

from kgiit.analyze.action_log import log_action, read_log


class TestActionLog(unittest.TestCase):

    def test_read_log_missing_file_returns_empty_list(self):
        self.assertEqual(read_log("does-not-exist.jsonl"), [])

    def test_log_action_writes_and_reads_back(self, tmp_path=None):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "actions.jsonl")

            entry = log_action(
                action="apply_label",
                status="applied",
                repo="octocat/Hello-World",
                issue_number=42,
                confirmed_by="github:octocat",
                suggestion={"labels_applied": ["bug", "priority:high"]},
                result={"labels_now_on_issue": ["bug", "priority:high"]},
                log_path=path,
            )

            self.assertEqual(entry["status"], "applied")
            self.assertEqual(entry["repo"], "octocat/Hello-World")
            self.assertIn("timestamp", entry)
            self.assertTrue(entry["timestamp"].endswith("Z"))

            entries = read_log(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["confirmed_by"], "github:octocat")

    def test_log_action_appends_multiple_entries_in_order(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "actions.jsonl")

            log_action(
                action="apply_label", status="declined", repo="a/b",
                issue_number=1, confirmed_by="alice", log_path=path,
            )
            log_action(
                action="apply_label", status="applied", repo="a/b",
                issue_number=1, confirmed_by="alice", log_path=path,
            )

            entries = read_log(path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["status"], "declined")
            self.assertEqual(entries[1]["status"], "applied")

    def test_read_log_skips_malformed_lines(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "actions.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"status": "applied", "repo": "a/b"}) + "\n")
                f.write("{not valid json\n")
                f.write(json.dumps({"status": "declined", "repo": "a/b"}) + "\n")

            entries = read_log(path)
            self.assertEqual(len(entries), 2)


if __name__ == "__main__":
    unittest.main()
