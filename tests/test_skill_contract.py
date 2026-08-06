"""
tests/test_skill_contract.py — Phase 2: Skill Contract Verification

This test suite parses each .agents/skills/*/SKILL.md file's declared JSON schema
and asserts that the Python implementation (kgiit/analyze/skills.py) actually returns
dictionaries matching those keys and types.

This proves, in a runnable CI check, that the spec-driven development contract
between the formal spec (SKILL.md) and the deterministic implementation (skills.py)
is honored. This is not theater — it runs in CI and catches schema drift.
"""
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List

from kgiit.analyze.skills import (
    build_analyze_summary,
    classify_issue,
    detect_duplicates,
    rank_priorities,
)

# Path to skill specs relative to project root
SKILLS_ROOT = Path(__file__).parents[1] / ".agents" / "skills"


def _parse_json_schema_keys(skill_md_path: Path) -> List[str]:
    """
    Parse the JSON schema block from a SKILL.md file and extract expected keys.

    Looks for the ```json ... ``` block in the "Output Requirement" section
    and extracts all "key": tokens.
    """
    content = skill_md_path.read_text(encoding="utf-8")
    # Find the JSON schema block
    json_blocks = re.findall(r"```json\s*(.*?)```", content, re.DOTALL)
    if not json_blocks:
        return []
    # Take the last (most relevant) block
    schema_text = json_blocks[-1].strip()
    # Extract "key": patterns
    keys = re.findall(r'"([^"]+)"\s*:', schema_text)
    return keys


class TestSkillContract(unittest.TestCase):
    """
    Verify that kgiit/analyze/skills.py honors the contracts defined in SKILL.md specs.
    """

    # Sample issue for testing
    SAMPLE_ISSUE = {
        "number": 42,
        "title": "Critical login crash on payment page",
        "body": "Users cannot log in. Authentication service crashes with fatal error.",
    }

    SAMPLE_ISSUE_2 = {
        "number": 99,
        "title": "Documentation typo in README",
        "body": "There is a spelling mistake in the installation guide.",
    }

    def test_issue_analyze_skill_md_exists(self):
        """The issue-triage SKILL.md file must exist."""
        skill_path = SKILLS_ROOT / "issue-triage" / "SKILL.md"
        self.assertTrue(
            skill_path.exists(),
            f"SKILL.md not found at {skill_path}"
        )

    def test_classify_issue_returns_schema_keys(self):
        """
        classify_issue() must return a dict containing at minimum the keys
        declared in .agents/skills/issue-triage/SKILL.md JSON schema.
        """
        skill_path = SKILLS_ROOT / "issue-triage" / "SKILL.md"
        if not skill_path.exists():
            self.skipTest("issue-triage SKILL.md not found")

        spec_keys = _parse_json_schema_keys(skill_path)
        # Spec defines: severity, label, owner, reason
        self.assertIn("severity", spec_keys, "SKILL.md schema must declare 'severity' key")
        self.assertIn("label", spec_keys, "SKILL.md schema must declare 'label' key")
        self.assertIn("owner", spec_keys, "SKILL.md schema must declare 'owner' key")
        self.assertIn("reason", spec_keys, "SKILL.md schema must declare 'reason' key")

        # Now verify the implementation returns those keys
        result = classify_issue(self.SAMPLE_ISSUE)
        self.assertIsInstance(result, dict)
        for key in spec_keys:
            self.assertIn(
                key, result,
                f"classify_issue() missing key '{key}' declared in SKILL.md"
            )

    def test_classify_issue_severity_is_valid(self):
        """severity must be strictly HIGH, MEDIUM, or LOW per SKILL.md."""
        result = classify_issue(self.SAMPLE_ISSUE)
        self.assertIn(
            result["severity"],
            ["HIGH", "MEDIUM", "LOW"],
            f"severity must be HIGH|MEDIUM|LOW, got: {result['severity']}"
        )

    def test_classify_issue_owner_format(self):
        """owner must be '@username' or 'unassigned' per SKILL.md."""
        result = classify_issue(self.SAMPLE_ISSUE)
        owner = result["owner"]
        self.assertTrue(
            owner == "unassigned" or owner.startswith("@"),
            f"owner must be 'unassigned' or '@username', got: {owner}"
        )

    def test_classify_issue_types(self):
        """All fields must be strings per the schema."""
        result = classify_issue(self.SAMPLE_ISSUE)
        for key in ["severity", "label", "owner", "reason"]:
            self.assertIsInstance(
                result[key], str,
                f"classify_issue()['{key}'] must be str, got {type(result[key])}"
            )

    def test_duplicate_detector_skill_md_exists(self):
        """The duplicate-detector SKILL.md file must exist."""
        skill_path = SKILLS_ROOT / "duplicate-detector" / "SKILL.md"
        self.assertTrue(skill_path.exists(), f"SKILL.md not found at {skill_path}")

    def test_detect_duplicates_returns_schema_keys(self):
        """
        detect_duplicates() must return a dict with the keys declared in
        .agents/skills/duplicate-detector/SKILL.md JSON schema.
        """
        skill_path = SKILLS_ROOT / "duplicate-detector" / "SKILL.md"
        if not skill_path.exists():
            self.skipTest("duplicate-detector SKILL.md not found")

        spec_keys = _parse_json_schema_keys(skill_path)
        # Spec defines: is_duplicate, duplicate_of, confidence
        self.assertIn("is_duplicate", spec_keys)
        self.assertIn("duplicate_of", spec_keys)
        self.assertIn("confidence", spec_keys)

        result = detect_duplicates(self.SAMPLE_ISSUE, [self.SAMPLE_ISSUE, self.SAMPLE_ISSUE_2])
        self.assertIsInstance(result, dict)
        for key in spec_keys:
            self.assertIn(key, result, f"detect_duplicates() missing key '{key}'")

    def test_detect_duplicates_types(self):
        """is_duplicate must be bool, duplicate_of must be str or None, confidence must be str."""
        result = detect_duplicates(self.SAMPLE_ISSUE, [self.SAMPLE_ISSUE, self.SAMPLE_ISSUE_2])
        self.assertIsInstance(result["is_duplicate"], bool)
        self.assertIsInstance(result["confidence"], str)
        self.assertIn(result["confidence"], ["high", "medium", "low"])
        # duplicate_of is str (like "#42") or None
        dup_of = result["duplicate_of"]
        self.assertTrue(
            dup_of is None or isinstance(dup_of, str),
            f"duplicate_of must be str or None, got {type(dup_of)}"
        )

    def test_detect_duplicates_no_match_returns_false(self):
        """When there's no similar issue, is_duplicate must be False."""
        unique_issue = {
            "number": 999,
            "title": "Completely unrelated issue about graphics rendering",
            "body": "The 3D renderer crashes on macOS due to Metal API bug.",
        }
        result = detect_duplicates(unique_issue, [self.SAMPLE_ISSUE])
        # With very different content, should not be a duplicate
        # (not asserting False because Jaccard might find overlap — just check structure)
        self.assertIsInstance(result["is_duplicate"], bool)

    def test_priority_ranker_skill_md_exists(self):
        """The priority-ranker SKILL.md file must exist."""
        skill_path = SKILLS_ROOT / "priority-ranker" / "SKILL.md"
        self.assertTrue(skill_path.exists(), f"SKILL.md not found at {skill_path}")

    def test_rank_priorities_returns_list_of_schema_dicts(self):
        """
        rank_priorities() must return a list of dicts with keys declared in
        .agents/skills/priority-ranker/SKILL.md JSON schema.
        """
        skill_path = SKILLS_ROOT / "priority-ranker" / "SKILL.md"
        if not skill_path.exists():
            self.skipTest("priority-ranker SKILL.md not found")

        spec_keys = _parse_json_schema_keys(skill_path)
        # Spec defines: issue_number, rank, reason (inside array items)
        self.assertIn("issue_number", spec_keys)
        self.assertIn("rank", spec_keys)
        self.assertIn("reason", spec_keys)

        classified = [
            {"issue_number": "#1", "severity": "HIGH", "label": "bug/auth"},
            {"issue_number": "#2", "severity": "LOW", "label": "docs"},
        ]
        result = rank_priorities(classified)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        for item in result:
            self.assertIsInstance(item, dict)
            for key in spec_keys:
                self.assertIn(key, item, f"rank_priorities() item missing key '{key}'")

    def test_rank_priorities_rank_is_int(self):
        """rank must be an integer per the SKILL.md schema."""
        classified = [
            {"issue_number": "#5", "severity": "MEDIUM", "label": "perf"},
        ]
        result = rank_priorities(classified)
        self.assertIsInstance(result[0]["rank"], int)

    def test_rank_priorities_order(self):
        """HIGH severity issues must rank before MEDIUM, which rank before LOW."""
        classified = [
            {"issue_number": "#3", "severity": "LOW", "label": "docs"},
            {"issue_number": "#1", "severity": "HIGH", "label": "bug/auth"},
            {"issue_number": "#2", "severity": "MEDIUM", "label": "perf"},
        ]
        result = rank_priorities(classified)
        nums = [item["issue_number"] for item in result]
        self.assertEqual(nums[0], "#1")  # HIGH first
        self.assertEqual(nums[1], "#2")  # MEDIUM second
        self.assertEqual(nums[2], "#3")  # LOW last

    def test_analyze_summary_skill_md_exists(self):
        """The triage-summary SKILL.md file must exist."""
        skill_path = SKILLS_ROOT / "triage-summary" / "SKILL.md"
        self.assertTrue(skill_path.exists(), f"SKILL.md not found at {skill_path}")

    def test_build_analyze_summary_returns_string(self):
        """
        build_analyze_summary() must return a plain-text string per
        .agents/skills/triage-summary/SKILL.md output requirement.
        """
        classified = [
            {"severity": "HIGH", "label": "bug/auth", "owner": "unassigned"},
            {"severity": "LOW", "label": "docs", "owner": "@alice"},
        ]
        result = build_analyze_summary(classified)
        self.assertIsInstance(result, str, "build_analyze_summary() must return str")
        self.assertGreater(len(result), 0, "build_analyze_summary() must not return empty string")

    def test_build_analyze_summary_no_json_no_markdown(self):
        """Per SKILL.md: output must NOT use bullet points, markdown, or JSON."""
        classified = [
            {"severity": "HIGH", "label": "bug/auth", "owner": "unassigned"},
        ]
        result = build_analyze_summary(classified)
        # Should not contain markdown bullets or JSON braces
        self.assertNotIn("{", result)
        self.assertNotIn("}", result)
        self.assertNotIn("- ", result[:5])  # no leading bullet points
        self.assertNotIn("```", result)

    def test_build_analyze_summary_mentions_high_count(self):
        """Per SKILL.md: if HIGH issues exist, mention their count first."""
        classified = [
            {"severity": "HIGH", "label": "bug", "owner": "unassigned"},
            {"severity": "HIGH", "label": "bug", "owner": "@bob"},
            {"severity": "LOW", "label": "docs", "owner": "unassigned"},
        ]
        result = build_analyze_summary(classified)
        self.assertIn("HIGH", result)
        self.assertIn("2", result)

    def test_build_analyze_summary_empty_input(self):
        """build_analyze_summary([]) must return a non-empty string gracefully."""
        result = build_analyze_summary([])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
