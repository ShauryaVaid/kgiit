"""
tests/test_bug_fixes.py — Regression tests for all 4 user-reported bugs.

Bug 1: Raw Rich markup tags printed as literal text in banner (modes section).
Bug 2: GUI mode (option 2) crashes with FileNotFoundError when Electron not installed.
Bug 3: No way to continue to next lesson/track after completion.
Bug 4: GitHub API rate limit shows raw JSON dump with no actionable guidance.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Bug 1 — Markup rendering: modes Text leaked raw [bold ...] strings
# ---------------------------------------------------------------------------

class TestBug1MarkupRendering:
    """Verify that Rich markup tags are NOT emitted as literal text in the banner."""

    def test_banner_does_not_emit_raw_markup_tags(self, capsys):
        """_print_kgiit_banner() must not output literal [bold #...] strings."""
        from kgiit.cli import _print_kgiit_banner
        _print_kgiit_banner()
        out = capsys.readouterr().out
        # These exact markup strings were leaking before the fix in the modes section
        assert "[bold #ff007f]" not in out, "Raw Rich markup tag leaked: [bold #ff007f]"
        assert "[bold #00f2fe]" not in out, "Raw Rich markup tag leaked: [bold #00f2fe]"
        assert "[dim #a0a5b5]" not in out, "Raw Rich markup tag leaked: [dim #a0a5b5]"

    def test_banner_contains_door_labels(self, capsys):
        """Door 1 and Door 2 must appear as rendered text (not as markup tags)."""
        from kgiit.cli import _print_kgiit_banner
        _print_kgiit_banner()
        out = capsys.readouterr().out
        assert "Door 1" in out, "Door 1 text must appear in banner output"
        assert "Door 2" in out, "Door 2 text must appear in banner output"

    def test_banner_contains_analyze_and_learn(self, capsys):
        """Product names 'analyze' and 'learn' must appear in the rendered output."""
        from kgiit.cli import _print_kgiit_banner
        _print_kgiit_banner()
        out = capsys.readouterr().out
        assert "analyze" in out.lower()
        assert "learn" in out.lower()


# ---------------------------------------------------------------------------
# Bug 2 — GUI mode: FileNotFoundError handled gracefully
# ---------------------------------------------------------------------------

class TestBug2GUICrash:
    """Verify GUI mode falls back to TUI without crashing when Electron is missing."""

    def test_launch_gui_falls_back_when_npx_not_found(self):
        """When npx probe raises FileNotFoundError, must fall back to TUI."""
        from kgiit.learn.curriculum import ALL_TRACKS
        from kgiit.learn.cli import _launch_gui

        track = ALL_TRACKS[0]

        with patch("kgiit.learn.cli.subprocess.run", side_effect=FileNotFoundError):
            with patch("kgiit.learn.cli._launch_tui") as mock_tui:
                _launch_gui(track)
                mock_tui.assert_called_once_with(track, headless=False)

    def test_launch_gui_shows_install_instructions_when_npx_missing(self, capsys):
        """When npx is not found, a helpful install message must be printed."""
        from kgiit.learn.curriculum import ALL_TRACKS
        from kgiit.learn.cli import _launch_gui

        track = ALL_TRACKS[0]

        with patch("kgiit.learn.cli.subprocess.run", side_effect=FileNotFoundError):
            with patch("kgiit.learn.cli._launch_tui"):
                _launch_gui(track)

        out = capsys.readouterr().out
        # Must mention how to fix it
        assert "nodejs.org" in out.lower() or "Node.js" in out or "npm install" in out

    def test_launch_gui_does_not_raise_on_missing_npx(self):
        """Must not propagate FileNotFoundError to the caller."""
        from kgiit.learn.curriculum import ALL_TRACKS
        from kgiit.learn.cli import _launch_gui

        track = ALL_TRACKS[0]

        with patch("kgiit.learn.cli.subprocess.run", side_effect=FileNotFoundError):
            with patch("kgiit.learn.cli._launch_tui"):
                # This must NOT raise
                try:
                    _launch_gui(track)
                except FileNotFoundError:
                    pytest.fail("_launch_gui raised FileNotFoundError — must not crash")


# ---------------------------------------------------------------------------
# Bug 3 — Next lesson/track progression after completion
# ---------------------------------------------------------------------------

class TestBug3NextTrackProgression:
    """Verify that after completing a track the user is offered the next one."""

    def test_next_track_prompt_is_shown_after_completion(self):
        """After TUI exits, launch_learn_interactive must prompt about next track."""
        from kgiit.learn.curriculum import ALL_TRACKS
        from kgiit.learn import cli as learn_cli

        if len(ALL_TRACKS) < 2:
            pytest.skip("Need at least 2 tracks to test next-track progression")

        track_0 = ALL_TRACKS[0]

        with patch("kgiit.learn.cli._select_track", return_value=track_0), \
             patch("kgiit.learn.cli._select_mode", return_value="terminal"), \
             patch("kgiit.learn.cli._launch_tui"), \
             patch("kgiit.learn.cli.console") as mock_console:

            mock_console.input.return_value = "n"
            learn_cli.launch_learn_interactive()

            # Must have prompted at least once about next track
            mock_console.input.assert_called_once()

    def test_next_track_launches_on_yes(self):
        """When user answers 'y', the next track must be launched."""
        from kgiit.learn.curriculum import ALL_TRACKS
        from kgiit.learn import cli as learn_cli

        if len(ALL_TRACKS) < 2:
            pytest.skip("Need at least 2 tracks to test next-track progression")

        track_0 = ALL_TRACKS[0]

        with patch("kgiit.learn.cli._select_track", return_value=track_0), \
             patch("kgiit.learn.cli._select_mode", return_value="terminal"), \
             patch("kgiit.learn.cli._launch_tui") as mock_tui, \
             patch("kgiit.learn.cli.console") as mock_console:

            mock_console.input.return_value = "y"
            learn_cli.launch_learn_interactive()

            # Called for first track AND second track
            assert mock_tui.call_count == 2

    def test_no_prompt_if_on_last_track(self):
        """On the last track, user must NOT be prompted (nothing to continue to)."""
        from kgiit.learn.curriculum import ALL_TRACKS
        from kgiit.learn import cli as learn_cli

        last_track = ALL_TRACKS[-1]

        with patch("kgiit.learn.cli._select_track", return_value=last_track), \
             patch("kgiit.learn.cli._select_mode", return_value="terminal"), \
             patch("kgiit.learn.cli._launch_tui"), \
             patch("kgiit.learn.cli.console") as mock_console:

            learn_cli.launch_learn_interactive()

            # input() must NOT be called — no next track to offer
            mock_console.input.assert_not_called()


# ---------------------------------------------------------------------------
# Bug 4 — Rate limit error: actionable panel instead of raw JSON
# ---------------------------------------------------------------------------

class TestBug4RateLimitError:
    """Verify rate limit error shows actionable guidance, not raw JSON dump."""

    def test_rate_limit_shows_github_token_instructions(self, capsys):
        """GitHubRateLimitError must print GITHUB_TOKEN instructions."""
        from kgiit.analyze import GitHubRateLimitError
        from click.testing import CliRunner
        from kgiit.analyze.cli import analyze_cmd

        runner = CliRunner()

        with patch("kgiit.analyze.cli.GitHubClient") as MockClient:
            instance = MockClient.return_value
            instance.list_open_issues.side_effect = GitHubRateLimitError(
                "GitHub API rate limit exceeded (403): {\"message\":\"rate limited\"}"
            )
            result = runner.invoke(analyze_cmd, ["--repo", "test/repo", "--all-open"])

        output = result.output
        assert "GITHUB_TOKEN" in output, "Must mention GITHUB_TOKEN in rate limit message"
        assert '{"message"' not in output, "Must not dump raw JSON in user output"
        assert "github.com/settings/tokens" in output, "Must link to token page"

    def test_rate_limit_exits_with_code_1(self):
        """Rate limit error must result in exit code 1."""
        from kgiit.analyze import GitHubRateLimitError
        from click.testing import CliRunner
        from kgiit.analyze.cli import analyze_cmd

        runner = CliRunner()

        with patch("kgiit.analyze.cli.GitHubClient") as MockClient:
            instance = MockClient.return_value
            instance.list_open_issues.side_effect = GitHubRateLimitError("rate limit")
            result = runner.invoke(analyze_cmd, ["--repo", "test/repo", "--all-open"])

        assert result.exit_code == 1

    def test_rate_limit_message_mentions_60_limit(self, capsys):
        """Error message must explain the 60 requests/hour unauthenticated limit."""
        from kgiit.analyze import GitHubRateLimitError
        from click.testing import CliRunner
        from kgiit.analyze.cli import analyze_cmd

        runner = CliRunner()

        with patch("kgiit.analyze.cli.GitHubClient") as MockClient:
            instance = MockClient.return_value
            instance.list_open_issues.side_effect = GitHubRateLimitError("rate limit")
            result = runner.invoke(analyze_cmd, ["--repo", "test/repo", "--all-open"])

        assert "60" in result.output, "Must mention the 60 req/hr limit"
