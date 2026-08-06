"""
tests/test_sandbox.py — Phase 5: Sandbox Engine Tests

Tests the safety-critical sandbox isolation engine.
The most important test here is test_escape_prevention, which verifies
that the sandbox refuses to execute any command whose working directory
is outside the sandbox root.

This is the single most important safety property in the project.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kgiit.learn.sandbox import (
    SandboxEscapeError,
    SandboxSession,
    list_sessions,
    purge_all_sessions,
    SANDBOX_ROOT,
)


class TestSandboxSafety(unittest.TestCase):
    """Tests for the critical sandbox safety properties."""

    def setUp(self):
        """Create a fresh sandbox session for each test."""
        self.session = SandboxSession(fixture="init")

    def tearDown(self):
        """Clean up the sandbox session after each test."""
        try:
            self.session.purge()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # CRITICAL SAFETY TEST — must never be skipped or removed
    # ------------------------------------------------------------------

    def test_escape_prevention_raises_error(self):
        """
        SAFETY: Running a command with cwd outside sandbox root MUST raise SandboxEscapeError.

        This test verifies the primary safety guarantee of the sandbox engine.
        The user's real filesystem must never be accessible from a practice session.
        """
        # Try to escape to a parent directory
        outside_path = Path(tempfile.gettempdir()) / "kgiit_escape_test"
        outside_path.mkdir(exist_ok=True)
        try:
            with self.assertRaises(SandboxEscapeError):
                self.session.run(["echo", "ESCAPED"], cwd=outside_path)
        finally:
            shutil.rmtree(outside_path, ignore_errors=True)

    def test_escape_prevention_home_directory(self):
        """Cannot escape to user's home directory."""
        home = Path.home()
        with self.assertRaises(SandboxEscapeError):
            self.session.run(["git", "status"], cwd=home)

    def test_escape_prevention_root(self):
        """Cannot escape to filesystem root."""
        # On Windows, use a drive root; on Unix, use /
        if os.name == "nt":
            root_path = Path("C:\\")
        else:
            root_path = Path("/")
        with self.assertRaises(SandboxEscapeError):
            self.session.run(["echo", "test"], cwd=root_path)

    def test_escape_prevention_parent_of_sandbox(self):
        """Cannot escape to the parent of the sandbox root."""
        parent = self.session.root.parent  # the sandboxes/ directory
        # The parent IS still inside SANDBOX_ROOT, but NOT inside this session's root
        with self.assertRaises(SandboxEscapeError):
            self.session.run(["echo", "test"], cwd=parent)

    def test_commands_inside_sandbox_succeed(self):
        """Commands inside the sandbox must work normally."""
        result = self.session.run(["git", "status"], cwd=self.session.repo_dir)
        # Should not raise and should succeed
        self.assertIsNotNone(result)
        self.assertIn(result.returncode, [0, 1])  # 0=ok, 1=no commits yet

    def test_sandbox_uses_throwaway_gitconfig(self):
        """The sandbox must use its own git config, not ~/.gitconfig."""
        env = self.session._get_env()
        self.assertIn("GIT_CONFIG_GLOBAL", env)
        config_path = Path(env["GIT_CONFIG_GLOBAL"])
        self.assertTrue(config_path.exists())
        # Must be inside the sandbox root
        config_path.resolve().relative_to(self.session.root.resolve())  # raises if not

    def test_gitconfig_never_touches_real_home(self):
        """The session's HOME must point inside the sandbox, not user's real home."""
        env = self.session._get_env()
        session_home = Path(env.get("HOME", ""))
        real_home = Path.home()
        self.assertNotEqual(
            str(session_home.resolve()),
            str(real_home.resolve()),
            "Session HOME must not equal user's real home directory"
        )

    def test_nosystem_config_flag_set(self):
        """GIT_CONFIG_NOSYSTEM must be set to prevent system gitconfig leakage."""
        env = self.session._get_env()
        self.assertEqual(env.get("GIT_CONFIG_NOSYSTEM"), "1")


class TestSandboxFixtures(unittest.TestCase):
    """Test that sandbox fixtures seed the repo correctly."""

    def _make_and_cleanup(self, fixture: str) -> SandboxSession:
        session = SandboxSession(fixture=fixture)
        self.addCleanup(session.purge)
        return session

    def test_empty_fixture_has_no_git_dir(self):
        """'empty' fixture: repo_dir exists but .git does NOT."""
        session = self._make_and_cleanup("empty")
        self.assertTrue(session.repo_dir.exists())
        self.assertFalse((session.repo_dir / ".git").exists())

    def test_init_fixture_has_git_dir(self):
        """'init' fixture: .git directory must exist."""
        session = self._make_and_cleanup("init")
        self.assertTrue((session.repo_dir / ".git").exists())

    def test_committed_fixture_has_commits(self):
        """'committed' fixture: must have at least one commit."""
        session = self._make_and_cleanup("committed")
        r = session.run(["git", "log", "--oneline"])
        self.assertEqual(r.returncode, 0)
        self.assertGreater(len(r.stdout.strip()), 0)

    def test_branched_fixture_has_feature_branch(self):
        """'branched' fixture: 'feature' branch must exist."""
        session = self._make_and_cleanup("branched")
        r = session.run(["git", "branch"])
        branches = r.stdout
        self.assertIn("feature", branches)
        self.assertIn("main", branches)

    def test_conflict_fixture_is_on_main(self):
        """'conflict' fixture: starts on main branch."""
        session = self._make_and_cleanup("conflict")
        state = session.get_state()
        self.assertEqual(state["branch"], "main")

    def test_unknown_fixture_raises(self):
        """Unknown fixture name must raise ValueError."""
        with self.assertRaises(ValueError):
            SandboxSession(fixture="nonexistent_fixture_xyz")


class TestSandboxState(unittest.TestCase):
    """Test get_state() returns correct information."""

    def setUp(self):
        self.session = SandboxSession(fixture="init")

    def tearDown(self):
        self.session.purge()

    def test_get_state_not_repo(self):
        """get_state() on empty fixture returns is_repo=False."""
        empty_session = SandboxSession(fixture="empty")
        self.addCleanup(empty_session.purge)
        state = empty_session.get_state()
        self.assertFalse(state["is_repo"])

    def test_get_state_is_repo(self):
        """get_state() on init fixture returns is_repo=True."""
        state = self.session.get_state()
        self.assertTrue(state["is_repo"])

    def test_get_state_untracked_files(self):
        """Creating a file shows it as untracked."""
        self.session.create_file("test.txt", "hello")
        state = self.session.get_state()
        self.assertIn("test.txt", state["untracked"])

    def test_get_state_staged_files(self):
        """Staging a file shows it in staged list."""
        self.session.create_file("staged.txt", "content")
        self.session.run(["git", "add", "staged.txt"])
        state = self.session.get_state()
        self.assertIn("staged.txt", state["staged"])


class TestSandboxReset(unittest.TestCase):
    """Test that reset() properly restores fixture state."""

    def setUp(self):
        self.session = SandboxSession(fixture="committed")

    def tearDown(self):
        self.session.purge()

    def test_reset_removes_new_files(self):
        """After reset, files created during the session must be gone."""
        # Create a file
        self.session.create_file("dirty.txt", "mess")
        self.assertTrue((self.session.repo_dir / "dirty.txt").exists())

        # Reset
        self.session.reset()

        # dirty.txt should be gone
        self.assertFalse((self.session.repo_dir / "dirty.txt").exists())

    def test_reset_restores_git_dir(self):
        """After reset, .git directory must exist for an init fixture."""
        session = SandboxSession(fixture="init")
        self.addCleanup(session.purge)

        session.reset()
        self.assertTrue((session.repo_dir / ".git").exists())


class TestSandboxSessionManagement(unittest.TestCase):
    """Test session listing and purging."""

    def test_list_sessions_includes_new_session(self):
        """A newly created session appears in list_sessions()."""
        session = SandboxSession(fixture="empty")
        sessions = list_sessions()
        self.assertIn(session.session_id, sessions)
        session.purge()

    def test_purge_removes_session_from_list(self):
        """After purge(), session no longer appears in list_sessions()."""
        session = SandboxSession(fixture="empty")
        sid = session.session_id
        session.purge()
        sessions = list_sessions()
        self.assertNotIn(sid, sessions)


if __name__ == "__main__":
    unittest.main()
