"""
kgiit.learn.sandbox — Isolated git practice sandbox engine.

SAFETY GUARANTEE: Every command executed by a SandboxSession is hard-checked
to ensure its working directory is inside the sandbox root. If it isn't,
SandboxEscapeError is raised and the command is refused. This is tested
explicitly in tests/test_sandbox.py::TestSandbox::test_escape_prevention.

Each session:
- Gets a fresh isolated directory: ~/.kgiit/sandboxes/<session-id>/
- Gets a throwaway .gitconfig scoped via GIT_CONFIG_GLOBAL (never touches
  the user's real ~/.gitconfig)
- Can be reset back to its fixture state on demand
- Can be fully deleted with purge()
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import uuid
from pathlib import Path
from typing import Any


def _rm_readonly_onerror(func, path, exc_info):
    """
    Windows-compatible rmtree error handler.
    Git sets read-only bits on .git/objects files. This handler
    clears the read-only flag and retries the removal.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass  # Best-effort; don't crash teardown


# Root directory for all sandbox sessions
SANDBOX_ROOT = Path.home() / ".kgiit" / "sandboxes"


class SandboxEscapeError(Exception):
    """
    Raised when a command's working directory is outside the sandbox root.
    This is the primary safety check — it is never allowed to be bypassed.
    """


class SandboxCommandError(Exception):
    """Raised when a git command fails inside the sandbox."""
    def __init__(self, message: str, returncode: int = -1, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class SandboxSession:
    """
    An isolated git practice environment.

    Each session lives in SANDBOX_ROOT/<session_id>/ and has its own
    throwaway git config. Commands are executed only inside this directory.
    """

    def __init__(self, fixture: str = "empty", session_id: str | None = None):
        """
        Create a new sandbox session.

        Args:
            fixture: Starting state for the sandbox repo. One of:
                     'empty'     — bare directory, no git repo yet
                     'init'      — initialized empty git repo
                     'committed' — repo with one initial commit
                     'branched'  — repo with main + feature branch
                     'conflict'  — repo pre-seeded with merge conflict
            session_id: If provided, resume an existing session. Otherwise
                        a new UUID is generated.
        """
        self.fixture = fixture
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.root = SANDBOX_ROOT / self.session_id
        self.repo_dir = self.root / "repo"
        self.config_file = self.root / "gitconfig"

        # Create the sandbox root
        SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
        self.root.mkdir(parents=True, exist_ok=True)

        # Write throwaway git config
        self._write_throwaway_gitconfig()

        # Seed the repo from fixture (only on fresh session)
        if not self.repo_dir.exists():
            self._seed_fixture(fixture)

    def _write_throwaway_gitconfig(self) -> None:
        """Write a minimal git config that won't touch the user's ~/.gitconfig."""
        config_content = (
            "[user]\n"
            "    name = kgiit-learner\n"
            "    email = learner@kgiit.local\n"
            "[init]\n"
            "    defaultBranch = main\n"
            "[core]\n"
            "    autocrlf = false\n"
            "[advice]\n"
            "    detachedHead = false\n"
        )
        self.config_file.write_text(config_content, encoding="utf-8")

    def _get_env(self) -> dict[str, str]:
        """Return env dict that scopes git to the throwaway config."""
        env = os.environ.copy()
        # Override git config — never touch user's real ~/.gitconfig
        env["GIT_CONFIG_GLOBAL"] = str(self.config_file)
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        # Disable terminal prompts (e.g. for passwords)
        env["GIT_TERMINAL_PROMPT"] = "0"
        # Ensure HOME doesn't leak real gitconfig
        env["HOME"] = str(self.root)
        return env

    def _assert_in_sandbox(self, path: Path) -> None:
        """
        SAFETY CHECK: Refuse to operate on any path outside the sandbox root.

        This is the most important safety property in the project. It is tested
        explicitly in tests/test_sandbox.py::TestSandbox::test_escape_prevention.
        """
        try:
            resolved = path.resolve()
            sandbox_resolved = self.root.resolve()
            # Use is_relative_to on Python 3.9+, fallback for 3.8
            try:
                resolved.relative_to(sandbox_resolved)
            except ValueError:
                raise SandboxEscapeError(
                    f"SAFETY VIOLATION: Path '{resolved}' is outside sandbox root '{sandbox_resolved}'. "
                    f"Command refused."
                )
        except SandboxEscapeError:
            raise
        except Exception as e:
            raise SandboxEscapeError(f"Could not verify path safety: {e}")

    def run(
        self,
        command: list[str],
        cwd: Path | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Execute a command inside the sandbox.

        Args:
            command: Command as list of strings (e.g. ['git', 'init'])
            cwd: Working directory. MUST be inside sandbox root. Defaults to repo_dir.
            check: If True, raise SandboxCommandError on non-zero exit code.

        Returns:
            subprocess.CompletedProcess with stdout/stderr captured.

        Raises:
            SandboxEscapeError: If cwd is outside the sandbox root.
            SandboxCommandError: If check=True and command exits non-zero.
        """
        work_dir = Path(cwd) if cwd is not None else self.repo_dir

        # SAFETY CHECK — must happen before any execution
        self._assert_in_sandbox(work_dir)

        result = subprocess.run(
            command,
            cwd=str(work_dir),
            env=self._get_env(),
            capture_output=True,
            text=True,
        )

        if check and result.returncode != 0:
            raise SandboxCommandError(
                f"Command {command} failed with exit code {result.returncode}",
                returncode=result.returncode,
                stderr=result.stderr,
            )

        return result

    def run_user_command(self, command_str: str) -> subprocess.CompletedProcess:
        """
        Execute a user-typed command string inside the sandbox repo_dir.

        The command is parsed via shell splitting and executed with the sandbox
        env. Always works in self.repo_dir.

        Returns:
            subprocess.CompletedProcess
        """
        import shlex
        try:
            command = shlex.split(command_str)
        except ValueError as e:
            raise SandboxCommandError(f"Could not parse command: {e}")

        return self.run(command, cwd=self.repo_dir)

    def get_state(self) -> dict[str, Any]:
        """
        Return a snapshot of the current sandbox git repo state.

        Returns dict with:
            branch (str): current branch name or "(detached HEAD)"
            staged (list[str]): staged file paths
            unstaged (list[str]): modified but unstaged file paths
            untracked (list[str]): new untracked files
            last_commit (str): short hash + message of HEAD, or None
            is_repo (bool): whether .git directory exists
        """
        state = {
            "branch": None,
            "staged": [],
            "unstaged": [],
            "untracked": [],
            "last_commit": None,
            "is_repo": (self.repo_dir / ".git").exists(),
        }

        if not state["is_repo"]:
            return state

        # Branch
        try:
            r = self.run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            if r.returncode == 0:
                branch = r.stdout.strip()
                state["branch"] = branch if branch != "HEAD" else "(detached HEAD)"
        except Exception:
            pass

        # Staged / Unstaged / Untracked
        try:
            r = self.run(["git", "status", "--porcelain"])
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    if len(line) < 2:
                        continue
                    index_status = line[0]
                    worktree_status = line[1]
                    path = line[3:].strip()
                    if index_status != " " and index_status != "?":
                        state["staged"].append(path)
                    if worktree_status == "M" or worktree_status == "D":
                        state["unstaged"].append(path)
                    if index_status == "?" and worktree_status == "?":
                        state["untracked"].append(path)
        except Exception:
            pass

        # Last commit
        try:
            r = self.run(["git", "log", "--oneline", "-1"])
            if r.returncode == 0 and r.stdout.strip():
                state["last_commit"] = r.stdout.strip()
        except Exception:
            pass

        return state

    def create_file(self, filename: str, content: str = "") -> Path:
        """Create a file inside the sandbox repo_dir."""
        filepath = self.repo_dir / filename
        self._assert_in_sandbox(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def reset(self) -> None:
        """Reset the sandbox back to its fixture starting state."""
        if self.repo_dir.exists():
            shutil.rmtree(self.repo_dir, onerror=_rm_readonly_onerror)
        self._seed_fixture(self.fixture)

    def purge(self) -> None:
        """Completely remove this sandbox session directory."""
        if self.root.exists():
            shutil.rmtree(self.root, onerror=_rm_readonly_onerror)

    # ------------------------------------------------------------------
    # Fixture seeding
    # ------------------------------------------------------------------

    def _seed_fixture(self, fixture: str) -> None:
        """Seed the sandbox repo_dir with the requested fixture state."""
        self.repo_dir.mkdir(parents=True, exist_ok=True)

        seeders = {
            "empty": self._seed_empty,
            "init": self._seed_init,
            "committed": self._seed_committed,
            "branched": self._seed_branched,
            "conflict": self._seed_conflict,
            "remote_sim": self._seed_remote_sim,
        }

        seeder = seeders.get(fixture)
        if seeder is None:
            raise ValueError(f"Unknown fixture '{fixture}'. Valid options: {list(seeders.keys())}")

        seeder()

    def _seed_empty(self) -> None:
        """Empty directory — no git repo yet."""
        # Nothing to do; repo_dir already created

    def _seed_init(self) -> None:
        """Initialized empty git repo."""
        self.run(["git", "init"], cwd=self.repo_dir, check=True)

    def _seed_committed(self) -> None:
        """Repo with one initial commit on main."""
        self.run(["git", "init"], cwd=self.repo_dir, check=True)
        readme = self.repo_dir / "README.md"
        readme.write_text("# kgiit sandbox\n\nPractice repository.\n", encoding="utf-8")
        self.run(["git", "add", "README.md"], cwd=self.repo_dir, check=True)
        self.run(
            ["git", "commit", "-m", "Initial commit: add README"],
            cwd=self.repo_dir,
            check=True,
        )

    def _seed_branched(self) -> None:
        """Repo with main branch + feature branch, one commit each."""
        self._seed_committed()
        self.run(["git", "branch", "feature"], cwd=self.repo_dir, check=True)
        # Add a commit on feature
        self.run(["git", "switch", "feature"], cwd=self.repo_dir, check=True)
        feature_file = self.repo_dir / "feature.txt"
        feature_file.write_text("New feature work\n", encoding="utf-8")
        self.run(["git", "add", "feature.txt"], cwd=self.repo_dir, check=True)
        self.run(
            ["git", "commit", "-m", "Add feature.txt"],
            cwd=self.repo_dir,
            check=True,
        )
        self.run(["git", "switch", "main"], cwd=self.repo_dir, check=True)

    def _seed_conflict(self) -> None:
        """Repo pre-seeded with conflicting changes between main and feature."""
        self._seed_committed()
        # Create a file on main
        conflict_file = self.repo_dir / "conflict.txt"
        conflict_file.write_text("main branch content\n", encoding="utf-8")
        self.run(["git", "add", "conflict.txt"], cwd=self.repo_dir, check=True)
        self.run(
            ["git", "commit", "-m", "Add conflict.txt on main"],
            cwd=self.repo_dir,
            check=True,
        )
        # Create feature branch with conflicting change
        self.run(["git", "branch", "feature"], cwd=self.repo_dir, check=True)
        self.run(["git", "switch", "feature"], cwd=self.repo_dir, check=True)
        conflict_file.write_text("feature branch content\n", encoding="utf-8")
        self.run(["git", "add", "conflict.txt"], cwd=self.repo_dir, check=True)
        self.run(
            ["git", "commit", "-m", "Modify conflict.txt on feature"],
            cwd=self.repo_dir,
            check=True,
        )
        # Return to main (merge will be done by the lesson)
        self.run(["git", "switch", "main"], cwd=self.repo_dir, check=True)

    def _seed_remote_sim(self) -> None:
        """Create a bare repository acting as a remote and an empty sandbox."""
        remote_dir = self.root / "remote.git"
        remote_dir.mkdir(parents=True, exist_ok=True)
        self.run(["git", "init", "--bare", "--initial-branch=main"], cwd=remote_dir, check=True)
        
        # User will start in an empty repo_dir to clone the remote
        self.repo_dir.mkdir(parents=True, exist_ok=True)


def list_sessions() -> list[str]:
    """Return a list of existing sandbox session IDs."""
    if not SANDBOX_ROOT.exists():
        return []
    return [d.name for d in SANDBOX_ROOT.iterdir() if d.is_dir()]


def purge_all_sessions() -> int:
    """Remove all sandbox sessions. Returns count of sessions removed."""
    sessions = list_sessions()
    for sid in sessions:
        session_dir = SANDBOX_ROOT / sid
        shutil.rmtree(session_dir, onerror=_rm_readonly_onerror)
    return len(sessions)
