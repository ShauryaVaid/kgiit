"""
kgiit — Two doors, one CLI.

1. kgiit analyze — Apply git/GitHub skills: analyze real issues in a repository
                  (needs internet, optional GITHUB_TOKEN)
                  Add --apply to confirm and write AI suggestions to real issues.
2. kgiit learn  — Practice git commands in a safe offline sandbox
                  (fully offline, no LLM, no external API)
3. kgiit log    — View the local write-back audit log
                  (fully offline, shows who confirmed what and when)
"""

__version__ = "1.2.0"
__author__ = "kgiit contributors"

__all__ = ["__version__"]
