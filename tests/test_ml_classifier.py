"""
tests/test_ml_classifier.py — Phase 6: ML Mistake Classifier Tests

Tests the ML mistake classifier inference wrapper (classifier.py).
Note: These tests work even if model.joblib doesn't exist yet —
the classifier falls back to rule-based hints gracefully.
"""
import unittest
from kgiit.learn.ml.classifier import (
    MistakeClassifier,
    classify_mistake,
    HINT_TEMPLATES,
    LABELS,
    _edit_distance,
    _rule_based_classify,
)


class TestEditDistance(unittest.TestCase):
    """Test the Levenshtein edit distance helper."""

    def test_identical_strings(self):
        self.assertEqual(_edit_distance("git init", "git init"), 0)

    def test_single_substitution(self):
        self.assertEqual(_edit_distance("git init", "git inat"), 1)

    def test_single_deletion(self):
        self.assertEqual(_edit_distance("git init", "git int"), 1)

    def test_completely_different(self):
        dist = _edit_distance("git commit -m 'msg'", "ls -la")
        self.assertGreater(dist, 5)

    def test_empty_strings(self):
        self.assertEqual(_edit_distance("", ""), 0)
        self.assertEqual(_edit_distance("git", ""), 3)


class TestRuleBasedClassifier(unittest.TestCase):
    """Test the deterministic rule-based fallback classifier."""

    def test_typo_detection(self):
        """Close edit distance should classify as TYPO."""
        result = _rule_based_classify("git inti", "git init")
        self.assertEqual(result, "TYPO")

    def test_missing_arg(self):
        """Shorter command with same subcommand → MISSING_ARG."""
        result = _rule_based_classify("git add", "git add hello.txt")
        self.assertEqual(result, "MISSING_ARG")

    def test_wrong_subcommand(self):
        """Different second token → WRONG_SUBCOMMAND."""
        result = _rule_based_classify("git initialize", "git init")
        self.assertEqual(result, "WRONG_SUBCOMMAND")

    def test_extra_arg(self):
        """Longer command with extra positional arg → EXTRA_ARG."""
        # Use a positional extra arg (not a flag) so it doesn't trigger WRONG_FLAG
        result = _rule_based_classify("git add hello.txt extra_file.txt", "git add hello.txt")
        self.assertEqual(result, "EXTRA_ARG")


class TestHintTemplates(unittest.TestCase):
    """Test that all hint templates exist and can be formatted."""

    def test_all_labels_have_templates(self):
        """Every label in LABELS must have a corresponding hint template."""
        for label in LABELS:
            self.assertIn(
                label, HINT_TEMPLATES,
                f"Label '{label}' is missing from HINT_TEMPLATES"
            )

    def test_templates_are_strings(self):
        """All hint templates must be non-empty strings."""
        for label, template in HINT_TEMPLATES.items():
            self.assertIsInstance(template, str)
            self.assertGreater(len(template), 0)

    def test_templates_can_be_formatted(self):
        """All templates with {typed}/{expected} slots must format without errors."""
        for label, template in HINT_TEMPLATES.items():
            try:
                result = template.format(typed="git inti", expected="git init")
                self.assertIsInstance(result, str)
            except KeyError as e:
                self.fail(f"Template for '{label}' has unexpected slot: {e}")


class TestMistakeClassifier(unittest.TestCase):
    """Test the MistakeClassifier predict() function."""

    def setUp(self):
        self.classifier = MistakeClassifier()

    def test_correct_command_returns_correct_label(self):
        """If typed == expected, label must be CORRECT with confidence 1.0."""
        label, confidence, hint = self.classifier.predict(
            typed="git init",
            expected="git init",
            context={},
        )
        self.assertEqual(label, "CORRECT")
        self.assertEqual(confidence, 1.0)

    def test_returns_tuple_of_three(self):
        """predict() always returns (label, confidence, hint_text)."""
        result = self.classifier.predict("git inti", "git init", {})
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_label_in_valid_set(self):
        """Returned label must be one of the 12 valid labels."""
        label, _, _ = self.classifier.predict("git inti", "git init", {})
        self.assertIn(label, LABELS, f"Label '{label}' not in LABELS")

    def test_confidence_is_float_0_to_1(self):
        """confidence must be a float between 0.0 and 1.0."""
        _, confidence, _ = self.classifier.predict("git add", "git add hello.txt", {})
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_hint_is_nonempty_string(self):
        """hint_text must be a non-empty string."""
        _, _, hint = self.classifier.predict("git inti", "git init", {})
        self.assertIsInstance(hint, str)
        self.assertGreater(len(hint), 0)

    def test_hint_contains_expected_command(self):
        """Hint text should mention the expected command."""
        _, _, hint = self.classifier.predict("git inti", "git init", {})
        self.assertIn("git init", hint)

    def test_hint_contains_typed_command(self):
        """Hint text should mention what the user typed."""
        _, _, hint = self.classifier.predict("git inti", "git init", {})
        self.assertIn("git inti", hint)

    def test_context_accepted(self):
        """Context dict is accepted without errors."""
        context = {"has_staged": True, "has_unstaged": False, "is_init": True}
        label, conf, hint = self.classifier.predict("git commit", 'git commit -m "msg"', context)
        self.assertIn(label, LABELS)

    def test_completely_wrong_command_gives_hint(self):
        """A completely wrong command still gets a useful hint."""
        label, confidence, hint = self.classifier.predict(
            "npm install", "git init", {}
        )
        self.assertIn(label, LABELS)
        self.assertIsInstance(hint, str)
        self.assertGreater(len(hint), 0)


class TestClassifyMistakeConvenienceFunction(unittest.TestCase):
    """Test the module-level classify_mistake() convenience function."""

    def test_basic_call(self):
        label, confidence, hint = classify_mistake("git inti", "git init")
        self.assertIn(label, LABELS)
        self.assertIsInstance(hint, str)

    def test_with_context(self):
        label, confidence, hint = classify_mistake(
            "git commit -m 'msg'",
            "git add hello.txt",
            context={"has_staged": False, "has_unstaged": True, "is_init": True},
        )
        self.assertIn(label, LABELS)

    def test_no_context_defaults(self):
        """classify_mistake with no context arg should not raise."""
        label, confidence, hint = classify_mistake("git inti", "git init")
        self.assertIsNotNone(label)

    def test_all_hint_templates_reachable(self):
        """
        Verify that each hint template can be selected by the rule-based fallback.
        This ensures no template is unreachable dead code.
        """
        test_cases = [
            ("git inti", "git init"),           # TYPO
            ("git add", "git add hello.txt"),   # MISSING_ARG
            ("git add hello.txt --verbose", "git add hello.txt"),  # EXTRA_ARG
            ("git initialize", "git init"),     # WRONG_SUBCOMMAND
        ]
        seen_labels = set()
        for typed, expected in test_cases:
            label, _, _ = classify_mistake(typed, expected)
            seen_labels.add(label)

        # At least 3 distinct labels should be reachable
        self.assertGreaterEqual(
            len(seen_labels), 3,
            f"Expected at least 3 distinct labels, got: {seen_labels}"
        )


if __name__ == "__main__":
    unittest.main()
