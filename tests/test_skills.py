import unittest
from triagectl.skills import (
    classify_issue,
    detect_duplicates,
    rank_priorities,
    build_triage_summary,
)


class TestSkills(unittest.TestCase):

    def test_classify_issue_high_auth(self):
        issue = {
            "number": 10,
            "title": "Critical login authentication crash",
            "body": "User login fails with fatal exception on payment page.",
        }
        res = classify_issue(issue)
        self.assertEqual(res["severity"], "HIGH")
        self.assertEqual(res["label"], "bug/auth")

    def test_classify_issue_low_docs(self):
        issue = {
            "number": 11,
            "title": "Fix typo in README documentation",
            "body": "Spelling mistake in installation guide.",
        }
        res = classify_issue(issue)
        self.assertEqual(res["severity"], "LOW")
        self.assertEqual(res["label"], "docs")

    def test_detect_duplicates(self):
        target = {
            "number": 1,
            "title": "Database connection timeout during authentication",
            "body": "The app hangs when trying to connect to the database on auth.",
        }
        existing = [
            target,
            {
                "number": 2,
                "title": "Database connection timeout during authentication",
                "body": "The app hangs when trying to connect to the database on auth.",
            },
        ]
        dup_res = detect_duplicates(target, existing)
        self.assertTrue(dup_res["is_duplicate"])
        self.assertEqual(dup_res["duplicate_of"], "#2")
        self.assertEqual(dup_res["confidence"], "high")

    def test_rank_priorities(self):
        classified = [
            {"issue_number": "#2", "severity": "LOW", "label": "docs"},
            {"issue_number": "#1", "severity": "HIGH", "label": "bug/auth"},
            {"issue_number": "#3", "severity": "MEDIUM", "label": "perf"},
        ]
        ranked = rank_priorities(classified)
        self.assertEqual(ranked[0]["issue_number"], "#1")
        self.assertEqual(ranked[1]["issue_number"], "#3")
        self.assertEqual(ranked[2]["issue_number"], "#2")

    def test_build_triage_summary(self):
        classified = [
            {"severity": "HIGH", "label": "bug/auth", "owner": "unassigned"},
            {"severity": "HIGH", "label": "bug/auth", "owner": "@alex"},
            {"severity": "LOW", "label": "docs", "owner": "unassigned"},
        ]
        summary = build_triage_summary(classified)
        self.assertIn("2 HIGH severity issues need attention, mostly in bug/auth.", summary)
        self.assertIn("2 issues remain unassigned.", summary)


if __name__ == "__main__":
    unittest.main()
