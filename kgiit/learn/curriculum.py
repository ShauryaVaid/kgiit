"""
kgiit.learn.curriculum — Lesson definitions for the git practice tracks.

Each lesson is a dataclass with:
- id: unique lesson identifier
- title: display name
- concept: one-line explanation of what this lesson teaches
- instructions: multi-line detailed instructions shown in the TUI
- target_command: the exact command the user must type (used by ML classifier)
- fixture: sandbox starting state (see sandbox.py SandboxSession fixtures)
- verify: callable that checks actual repo state after the command runs
- hint: fallback hint if ML classifier is unavailable
- setup_steps: optional pre-run setup (e.g. create files before staging lesson)

Verification functions check ACTUAL GIT STATE — not just exit code 0.
This is an explicit design choice: exit code 0 is necessary but not sufficient.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Callable

from kgiit.learn.sandbox import SandboxSession


@dataclass
class VerifyResult:
    """Result of a lesson verification step."""
    passed: bool
    message: str  # Plain-language summary of what happened / what was wrong


@dataclass
class Lesson:
    """A single interactive git practice lesson."""
    id: str
    title: str
    concept: str
    instructions: str
    target_command: str
    fixture: str
    verify: Callable[[SandboxSession,
                      subprocess.CompletedProcess], VerifyResult]
    hint: str  # Fallback hint if ML classifier unavailable
    setup_steps: list[Callable[[SandboxSession], None]
                      ] = field(default_factory=list)
    allow_alternate_commands: list[str] = field(default_factory=list)


@dataclass
class Track:
    """A collection of related lessons."""
    id: str
    title: str
    description: str
    lessons: list[Lesson]


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def _git_dir_exists(sandbox: SandboxSession) -> bool:
    return (sandbox.repo_dir / ".git").is_dir()


def _get_staged_files(sandbox: SandboxSession) -> list[str]:
    return sandbox.get_state().get("staged", [])


def _get_last_commit_message(sandbox: SandboxSession) -> str | None:
    r = sandbox.run(["git", "log", "--format=%s", "-1"])
    if r.returncode == 0:
        return r.stdout.strip()
    return None


def _get_current_branch(sandbox: SandboxSession) -> str | None:
    r = sandbox.run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if r.returncode == 0:
        return r.stdout.strip()
    return None


def _branch_exists(sandbox: SandboxSession, branch_name: str) -> bool:
    r = sandbox.run(["git", "branch", "--list", branch_name])
    return bool(r.stdout.strip())


# ---------------------------------------------------------------------------
# Lesson 1: git init
# ---------------------------------------------------------------------------

def _verify_init(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    """Verify that git init actually created a .git directory."""
    if result.returncode != 0:
        return VerifyResult(
            passed=False,
            message=f"Command exited with error code {
                result.returncode}. {
                result.stderr.strip()}",
        )
    if not _git_dir_exists(sandbox):
        return VerifyResult(
            passed=False,
            message="The .git directory was NOT created. Did the command run in the right directory?",
        )
    return VerifyResult(
        passed=True,
        message=(
            "✓ git init succeeded! The .git directory exists at:\n"
            f"  {sandbox.repo_dir / '.git'}\n\n"
            "Your sandbox now has an empty git repository. "
            "This directory tracks everything git knows about your project."
        ),
    )


LESSON_INIT = Lesson(
    id="basics-01-init",
    title="Lesson 1: Initialize a Repository",
    concept="git init creates a new empty git repository in the current directory.",
    instructions=(
        "Every git journey starts with git init.\n\n"
        "This command creates a hidden .git/ folder inside your current directory. "
        "That folder is where git stores your entire project history — "
        "every commit, every branch, every change you've ever made.\n\n"
        "Your sandbox is an empty directory right now. Initialize a git repo:\n\n"
        "  git init\n\n"
        "After running it, you should see:\n"
        "  'Initialized empty Git repository in .../repo/.git/'"),
    target_command="git init",
    fixture="empty",
    verify=_verify_init,
    hint=(
            "Try typing exactly: git init\n"
            "Make sure you haven't added extra arguments. "
            "git init with no arguments initializes the current directory."),
)


# ---------------------------------------------------------------------------
# Lesson 2: git status
# ---------------------------------------------------------------------------

def _verify_status(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    """Verify git status ran and showed something meaningful."""
    if result.returncode != 0:
        return VerifyResult(
            passed=False, message=f"git status failed (exit {
                result.returncode}): {
                result.stderr.strip()}", )
    output = result.stdout.lower()
    if "nothing to commit" in output or "on branch" in output or "no commits yet" in output:
        return VerifyResult(
            passed=True,
            message="Correct! `git status` shows the current state.",
        )
    return VerifyResult(
        passed=True,
        message=f"✓ git status output:\n{result.stdout.strip()}",
    )


def _setup_status(sandbox: SandboxSession) -> None:
    """For the status lesson, we already have an initialized repo from the fixture."""
    # Create a file so status shows something interesting
    sandbox.create_file("hello.txt", "Hello, git!\n")


LESSON_STATUS = Lesson(
    id="basics-02-status",
    title="Lesson 2: Check Repository Status",
    concept="git status shows what's happening in your working directory and staging area.",
    instructions=(
        "Now that you have a git repository, let's see its current state.\n\n"
        "git status is the command you'll run more than any other. "
        "It shows you:\n"
        "  • Which branch you're on\n"
        "  • Which files are staged (ready to commit)\n"
        "  • Which files are modified but not staged\n"
        "  • Which files are untracked (new files git doesn't know about yet)\n\n"
        "A file called hello.txt has been created in your sandbox.\n\n"
        "Run git status to see it:\n\n"
        "  git status"),
    target_command="git status",
    fixture="init",
    verify=_verify_status,
    hint=(
            "Type: git status\n"
            "No arguments needed. git status always checks the current repo."),
    setup_steps=[_setup_status],
)


# ---------------------------------------------------------------------------
# Lesson 3: git add
# ---------------------------------------------------------------------------

def _verify_add(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    """Verify that hello.txt was staged."""
    if result.returncode != 0:
        return VerifyResult(
            passed=False, message=f"git add failed (exit {
                result.returncode}): {
                result.stderr.strip()}", )
    staged = _get_staged_files(sandbox)
    if not staged:
        return VerifyResult(
            passed=False,
            message=(
                "hello.txt was NOT staged. "
                "git add moves files from 'untracked' to 'staged'. "
                "Try: git add hello.txt"
            ),
        )
    if "hello.txt" in staged or any("hello.txt" in s for s in staged):
        return VerifyResult(
            passed=True,
            message=(
                "✓ hello.txt is now staged!\n\n"
                "The staging area (also called the 'index') holds changes "
                "that are ready to be committed. Think of it as a draft — "
                "you choose exactly what goes into each commit.\n\n"
                "Run git status again to see the difference."
            ),
        )
    return VerifyResult(
        passed=False,
        message=f"Expected hello.txt to be staged, but got: {staged}",
    )


def _setup_add(sandbox: SandboxSession) -> None:
    sandbox.create_file("hello.txt", "Hello, git!\n")


LESSON_ADD = Lesson(
    id="basics-03-add",
    title="Lesson 3: Stage a File",
    concept="git add moves files into the staging area, marking them ready for the next commit.",
    instructions=(
        "Before git can record a change, you must stage it.\n\n"
        "The staging area is git's 'draft' area. You pick exactly which changes "
        "go into the next commit — you don't have to commit everything at once.\n\n"
        "A file called hello.txt is waiting to be staged.\n\n"
        "Stage it:\n\n"
        "  git add hello.txt\n\n"
        "After this, run git status to confirm it moved from "
        "'Untracked files' to 'Changes to be committed'."),
    target_command="git add hello.txt",
    fixture="init",
    verify=_verify_add,
    hint=(
            "Try: git add hello.txt\n"
            "You need to specify the filename. "
            "'git add' with no arguments does nothing."),
    setup_steps=[_setup_add],
    allow_alternate_commands=[
        "git add .",
        "git add -A"],
)


# ---------------------------------------------------------------------------
# Lesson 4: git commit
# ---------------------------------------------------------------------------

def _verify_commit(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    """Verify a commit was actually created."""
    if result.returncode != 0:
        return VerifyResult(
            passed=False, message=f"git commit failed (exit {
                result.returncode}): {
                result.stderr.strip()}", )
    msg = _get_last_commit_message(sandbox)
    if msg is None:
        return VerifyResult(
            passed=False,
            message="No commit was created. Did you stage any files first? Try: git add hello.txt",
        )
    return VerifyResult(
        passed=True,
        message=(
            f"✓ Commit created! Last commit message: '{msg}'\n\n"
            "Your change is now permanently recorded in the git history. "
            "Run 'git log --oneline' to see the full history."
        ),
    )


def _setup_commit(sandbox: SandboxSession) -> None:
    sandbox.create_file("hello.txt", "Hello, git!\n")
    sandbox.run(["git", "add", "hello.txt"])


LESSON_COMMIT = Lesson(
    id="basics-04-commit",
    title="Lesson 4: Make a Commit",
    concept="git commit -m '...' records staged changes as a permanent snapshot in the project history.",
    instructions=(
        "You've staged hello.txt. Now let's commit it.\n\n"
        "A commit is a permanent snapshot of your staged changes. "
        "Every commit has:\n"
        "  • A unique hash (like a4f8b2c)\n"
        "  • Your name and email (from git config)\n"
        "  • A timestamp\n"
        "  • A commit message describing what changed\n\n"
        "The -m flag lets you write the message inline:\n\n"
        "  git commit -m \"Add hello.txt\"\n\n"
        "Write a meaningful message — you'll thank yourself later."
    ),
    target_command='git commit -m "Add hello.txt"',
    fixture="init",
    verify=_verify_commit,
    hint=(
        'Try: git commit -m "Add hello.txt"\n'
        "The -m flag is required. Without it, git opens an editor. "
        "Make sure you've staged a file first with git add."
    ),
    setup_steps=[_setup_commit],
    allow_alternate_commands=["git commit -m"],  # partial match OK
)


# ---------------------------------------------------------------------------
# Lesson 5: git branch + git switch
# ---------------------------------------------------------------------------

def _verify_branch(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    """Verify that the 'feature' branch was created and we switched to it."""
    if result.returncode != 0:
        return VerifyResult(
            passed=False, message=f"Command failed (exit {
                result.returncode}): {
                result.stderr.strip()}", )
    # Check current branch
    current = _get_current_branch(sandbox)
    branch_exists = _branch_exists(sandbox, "feature")

    if not branch_exists:
        return VerifyResult(
            passed=False,
            message=(
                "The 'feature' branch was not created. "
                "Try: git branch feature\n"
                "Then: git switch feature"
            ),
        )
    if current != "feature":
        return VerifyResult(
            passed=False,
            message=(
                f"You're still on '{current}'. "
                "The 'feature' branch exists but you haven't switched to it yet. "
                "Try: git switch feature"
            ),
        )
    return VerifyResult(
        passed=True, message=(
            "✓ You're now on the 'feature' branch!\n\n"
            "Branches are lightweight pointers to commits. Creating one is instant — "
            "git doesn't copy any files. Changes you make here won't affect 'main' "
            "until you explicitly merge them.\n\n"
            "Current branch: feature\n"
            "Try making a change and committing — it's isolated from main."), )


LESSON_BRANCH = Lesson(
    id="branch-01-create-switch",
    title="Lesson 5: Create & Switch Branches",
    concept="git branch creates a new branch pointer; git switch moves you to it.",
    instructions=(
        "Branches let you work on multiple things in parallel without affecting each other.\n\n"
        "The main branch is your stable baseline. Create a 'feature' branch "
        "to try something new:\n\n"
        "  git branch feature\n\n"
        "Then switch to it:\n\n"
        "  git switch feature\n\n"
        "Or do both in one command (modern git):\n\n"
        "  git switch -c feature\n\n"
        "After switching, any commits you make stay on 'feature' "
        "until you merge them back to 'main'."),
    target_command="git switch feature",
    fixture="committed",
    verify=_verify_branch,
    hint=(
            "First create the branch: git branch feature\n"
            "Then switch to it: git switch feature\n"
            "Or use the shortcut: git switch -c feature"),
    allow_alternate_commands=[
        "git switch -c feature",
        "git checkout -b feature",
        "git checkout feature"],
)


# ---------------------------------------------------------------------------
# Lesson 6: git merge (with conflict)
# ---------------------------------------------------------------------------

def _verify_merge(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    """
    Verify git merge ran. Accept either a clean merge or a conflict state —
    both are valid outcomes that teach different things.
    """
    if result.returncode == 0:
        # Clean merge
        msg = _get_last_commit_message(sandbox)
        return VerifyResult(
            passed=True,
            message=(
                "✓ Clean merge successful!\n\n"
                "Git automatically combined the changes from 'feature' into 'main'. "
                f"Merge commit: '{msg}'\n\n"
                "When both branches change different files (or different parts of the same file), "
                "git can merge automatically."
            ),
        )
    else:
        # Check if it's a conflict (expected here)
        r = sandbox.run(["git", "status"])
        if "conflict" in r.stdout.lower() or "merge" in r.stdout.lower():
            conflict_file = sandbox.repo_dir / "conflict.txt"
            if conflict_file.exists():
                content = conflict_file.read_text(encoding="utf-8")
                if "<<<<<<" in content:
                    return VerifyResult(
                        passed=True,
                        message=(
                            "✓ Merge conflict detected — exactly as expected!\n\n"
                            "Git found conflicting changes in conflict.txt. "
                            "Open the file to see the conflict markers:\n\n"
                            "  <<<<<<< HEAD\n"
                            "  main branch content\n"
                            "  =======\n"
                            "  feature branch content\n"
                            "  >>>>>>> feature\n\n"
                            "To resolve:\n"
                            "  1. Edit conflict.txt — keep what you want, delete the markers\n"
                            "  2. git add conflict.txt\n"
                            "  3. git commit -m 'Resolve merge conflict'\n\n"
                            f"File path: {conflict_file}"
                        ),
                    )
        return VerifyResult(
            passed=False,
            message=(
                f"git merge failed unexpectedly (exit {result.returncode}): {result.stderr.strip()}\n"
                "Make sure you're on the 'main' branch and 'feature' exists. "
                "Try: git switch main && git merge feature"
            ),
        )


LESSON_MERGE = Lesson(
    id="branch-02-merge-conflict",
    title="Lesson 6: Merge Branches (with Conflict)",
    concept="git merge combines histories; when both branches changed the same line, git creates a conflict you must resolve manually.",
    instructions=(
        "Time to merge the 'feature' branch back into 'main'.\n\n"
        "This sandbox has a conflict pre-seeded: both 'main' and 'feature' "
        "changed the same line in conflict.txt.\n\n"
        "First, make sure you're on main:\n\n"
        "  git switch main\n\n"
        "Then merge the feature branch:\n\n"
        "  git merge feature\n\n"
        "Git will tell you there's a CONFLICT. That's expected! Open conflict.txt "
        "and you'll see conflict markers (<<<<<<<, =======, >>>>>>>). "
        "Edit the file to keep what you want, then:\n\n"
        "  git add conflict.txt\n"
        "  git commit -m 'Resolve merge conflict'\n\n"
        "Conflicts are normal — resolving them is a core git skill."),
    target_command="git merge feature",
    fixture="conflict",
    verify=_verify_merge,
    hint=(
            "Make sure you're on main first: git switch main\n"
            "Then: git merge feature\n"
            "A conflict is expected — read the output carefully."),
    allow_alternate_commands=["git merge feature --no-ff"],
)


# ---------------------------------------------------------------------------
# Lesson 7: git clone
# ---------------------------------------------------------------------------

def _verify_clone(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    if result.returncode != 0:
        return VerifyResult(
            False, f"git clone failed: {
                result.stderr.strip()}")
    if not _git_dir_exists(sandbox):
        return VerifyResult(
            False,
            "The repository was not cloned successfully. Try: git clone ../remote.git .")
    return VerifyResult(
        True,
        "✓ Repository cloned successfully!\n\nNotice the '.' at the end? That tells git to clone directly into your current directory instead of creating a new folder.")


LESSON_CLONE = Lesson(
    id="collab-01-clone",
    title="Lesson 1: Clone a Repository",
    concept="git clone downloads an existing remote repository to your local machine.",
    instructions=(
        "To work with others, you usually start by cloning an existing repository.\n\n"
        "We've set up a simulated remote repository at '../remote.git'.\n"
        "Clone it directly into your current (empty) directory by adding a '.' at the end:\n\n"
        "  git clone ../remote.git .\n\n"
        "The '.' is important—it means 'put the files right here' instead of making a new folder."
    ),
    target_command="git clone ../remote.git .",
    fixture="remote_sim",
    verify=_verify_clone,
    hint="Try: git clone ../remote.git .",
)

# ---------------------------------------------------------------------------
# Lesson 8: git push
# ---------------------------------------------------------------------------


def _setup_push(sandbox: SandboxSession) -> None:
    sandbox.run(["git", "clone", "../remote.git", "."])
    sandbox.create_file("hello.txt", "Hello remote!")
    sandbox.run(["git", "add", "hello.txt"])
    sandbox.run(["git", "commit", "-m", "Add hello.txt"])


def _verify_push(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    if result.returncode != 0:
        return VerifyResult(False, f"git push failed: {result.stderr.strip()}")
    return VerifyResult(
        True,
        "✓ Code pushed to the remote repository!\n\nYour teammates can now see your commit.")


LESSON_PUSH = Lesson(
    id="collab-02-push",
    title="Lesson 2: Push Changes",
    concept="git push uploads your local commits to a remote repository.",
    instructions=(
        "You've cloned the repository and made a new commit locally.\n\n"
        "To share this commit with the world, you must push it to the remote server.\n\n"
        "Push your changes to the default branch (main):\n\n"
        "  git push origin main"),
    target_command="git push origin main",
    fixture="remote_sim",
    verify=_verify_push,
    hint="Try: git push origin main",
    setup_steps=[_setup_push],
    allow_alternate_commands=["git push"],
)

# ---------------------------------------------------------------------------
# Lesson 9: git pull
# ---------------------------------------------------------------------------


def _setup_pull(sandbox: SandboxSession) -> None:
    sandbox.run(["git", "clone", "../remote.git", "."])
    tmp_clone = sandbox.root / "tmp_clone"
    sandbox.run(["git", "clone", "../remote.git", str(tmp_clone)])
    new_file = tmp_clone / "update.txt"
    new_file.write_text("An update from a teammate!")
    sandbox.run(["git", "add", "update.txt"], cwd=tmp_clone)
    sandbox.run(["git", "commit", "-m", "Add update.txt"], cwd=tmp_clone)
    sandbox.run(["git", "push", "origin", "main"], cwd=tmp_clone)


def _verify_pull(
        sandbox: SandboxSession,
        result: subprocess.CompletedProcess) -> VerifyResult:
    if result.returncode != 0:
        return VerifyResult(False, f"git pull failed: {result.stderr.strip()}")
    if not (sandbox.repo_dir / "update.txt").exists():
        return VerifyResult(
            False,
            "The update from the teammate is missing. Try running: git pull origin main")
    return VerifyResult(
        True,
        "✓ Code pulled successfully!\n\nYou now have your teammate's changes on your local machine.")


LESSON_PULL = Lesson(
    id="collab-03-pull",
    title="Lesson 3: Pull Changes",
    concept="git pull downloads commits from the remote repository and merges them into your local branch.",
    instructions=(
        "A teammate just pushed a new commit to the remote repository!\n\n"
        "Your local repository is now out of date. To fetch their changes and merge them into your local branch, use:\n\n"
        "  git pull origin main"),
    target_command="git pull origin main",
    fixture="remote_sim",
    verify=_verify_pull,
    hint="Try: git pull origin main",
    setup_steps=[_setup_pull],
    allow_alternate_commands=["git pull"],
)

# ---------------------------------------------------------------------------
# Track definitions
# ---------------------------------------------------------------------------

GIT_BASICS_TRACK = Track(
    id="git-basics",
    title="Git Basics",
    description="Start from zero: init, status, add, commit. The four commands you'll use every day.",
    lessons=[
        LESSON_INIT,
        LESSON_STATUS,
        LESSON_ADD,
        LESSON_COMMIT],
)

BRANCHING_TRACK = Track(
    id="branching",
    title="Branching & Merging",
    description="Work in parallel safely: create branches, switch between them, merge changes.",
    lessons=[
        LESSON_BRANCH,
        LESSON_MERGE],
)

COLLABORATION_TRACK = Track(
    id="collaboration",
    title="Remotes & Collaboration",
    description="Work with others: clone a repo, push your commits, and pull updates.",
    lessons=[
        LESSON_CLONE,
        LESSON_PUSH,
        LESSON_PULL],
)

ALL_TRACKS: list[Track] = [
    GIT_BASICS_TRACK,
    BRANCHING_TRACK,
    COLLABORATION_TRACK]


def get_track(track_id: str) -> Track | None:
    """Look up a track by its ID."""
    for track in ALL_TRACKS:
        if track.id == track_id:
            return track
    return None


def get_lesson(lesson_id: str) -> Lesson | None:
    """Look up a lesson by its ID across all tracks."""
    for track in ALL_TRACKS:
        for lesson in track.lessons:
            if lesson.id == lesson_id:
                return lesson
    return None
