import unittest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kgiit.analyze.formatting import (
    format_labels,
    truncate_text,
    print_banner,
    print_issues_table,
)


class TestFormatting(unittest.TestCase):

    def setUp(self):
        self.console = Console(record=True, width=120)

    def test_truncate_text(self):
        self.assertEqual(truncate_text("Short title", max_length=20), "Short title")
        self.assertEqual(
            truncate_text("This is a very long title that exceeds the limit", max_length=20),
            "This is a very lo...",
        )

    def test_format_labels(self):
        self.assertEqual(format_labels([]), "[dim]none[/dim]")
        formatted = format_labels(["bug", "critical"])
        self.assertIn("bug", formatted)
        self.assertIn("critical", formatted)

    def test_print_banner(self):
        panel = print_banner("octocat/Hello-World", console=self.console)
        self.assertIsInstance(panel, Panel)
        output = self.console.export_text()
        self.assertIn("octocat/Hello-World", output)

    def test_print_issues_table(self):
        issues = [
            {
                "number": 101,
                "title": "A very long issue title that needs truncation for clean display",
                "labels": ["bug", "ui"],
                "comments": 3,
                "url": "https://github.com/octocat/Hello-World/issues/101",
            },
            {
                "number": 102,
                "title": "Short title",
                "labels": [],
                "comments": 0,
                "url": "https://github.com/octocat/Hello-World/issues/102",
            },
        ]
        table = print_issues_table(issues, console=self.console)
        self.assertIsInstance(table, Table)
        output = self.console.export_text()
        self.assertIn("#101", output)
        self.assertIn("#102", output)
        self.assertIn("bug", output)
        self.assertIn("Short title", output)


if __name__ == "__main__":
    unittest.main()
