"""
kgiit.learn.server — FastAPI bridge for the Electron GUI.
"""
from __future__ import annotations

import os
import subprocess
import hmac

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kgiit.learn.curriculum import get_track, ALL_TRACKS
from kgiit.learn.ml.classifier import classify_mistake
from kgiit.learn.sandbox import SandboxSession, SandboxCommandError

# Ensure the auth token exists if running under CLI bridge
EXPECTED_TOKEN = os.environ.get("KGIIT_AUTH_TOKEN")


def verify_token(x_auth_token: str = Header(None)):
    if EXPECTED_TOKEN and (not x_auth_token or not hmac.compare_digest(x_auth_token, EXPECTED_TOKEN)):
        raise HTTPException(status_code=403,
                            detail="Invalid or missing X-Auth-Token")
    return x_auth_token


app = FastAPI(title="kgiit GUI Bridge", dependencies=[
              Depends(verify_token)] if EXPECTED_TOKEN else [])

app.add_middleware(
    CORSMiddleware,
    # Since it's a local Electron app, we allow file:// etc, but the Auth
    # Token is the actual protection
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for the bridge
# mapping: session_id -> SandboxSession
_sessions: dict[str, SandboxSession] = {}


class TrackStartRequest(BaseModel):
    track_id: str


class ExecuteRequest(BaseModel):
    command: str


class VerifyRequest(BaseModel):
    """Schema for the verify_lesson endpoint body."""
    track_id: str
    lesson_index: int = 0
    last_command: str = ""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""


@app.get("/api/tracks")
def list_tracks():
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "lessons_count": len(t.lessons)
        }
        for t in ALL_TRACKS
    ]


@app.post("/api/session/start")
def start_session(req: TrackStartRequest):
    track = get_track(req.track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # We will just start with the first lesson's fixture
    first_lesson = track.lessons[0]
    session = SandboxSession(first_lesson.fixture)
    _sessions[session.session_id] = session
    return {
        "session_id": session.session_id,
        "track_title": track.title,
        "lesson_title": first_lesson.title,
        "lesson_prompt": first_lesson.instructions,
        "total_lessons": len(track.lessons),
        "current_index": 0
    }


@app.post("/api/session/{session_id}/execute")
def execute_command(session_id: str, req: ExecuteRequest):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    command = req.command.strip()

    try:
        proc = session.run_user_command(command)
        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except SandboxCommandError as e:
        return {
            "command": command,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(e)
        }
    except FileNotFoundError:
        binary = command.split()[0] if command else "Command"
        return {
            "command": command,
            "exit_code": 127,
            "stdout": "",
            "stderr": f"{binary}: command not found (Note: shell built-ins like 'cd' are not supported in this sandbox)"
        }
    except Exception as e:
        return {
            "command": command,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"System Error: {e}"
        }


@app.get("/api/session/{session_id}/status")
def get_status(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    state = session.get_state()
    return state


@app.post("/api/session/{session_id}/verify")
def verify_lesson(session_id: str, req: VerifyRequest):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    track_id = req.track_id
    lesson_index = req.lesson_index
    last_command = req.last_command
    exit_code = req.exit_code
    stdout = req.stdout
    stderr = req.stderr

    track = get_track(track_id)
    if not track or lesson_index >= len(track.lessons):
        raise HTTPException(status_code=400, detail="Invalid track or lesson")

    lesson = track.lessons[lesson_index]
    session = _sessions[session_id]

    # Mock a CompletedProcess for the verify signature
    mock_proc = subprocess.CompletedProcess(
        args=last_command,
        returncode=exit_code,
        stdout=stdout,
        stderr=stderr)

    result = lesson.verify(session, mock_proc)

    hint = None
    if not result.passed and last_command.startswith("git "):
        _, _, hint = classify_mistake(
            last_command, lesson.target_command, context=session.get_state())

    return {
        "passed": result.passed,
        "message": result.message,
        "hint": hint,
        "expected_command": lesson.target_command
    }


@app.post("/api/session/{session_id}/lesson/{lesson_index}/setup")
def setup_lesson(session_id: str, lesson_index: int, req: dict):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    track_id = req.get("track_id")
    track = get_track(track_id)
    if not track or lesson_index >= len(track.lessons):
        raise HTTPException(status_code=400, detail="Invalid track or lesson")

    lesson = track.lessons[lesson_index]
    session = _sessions[session_id]

    # Reset to the fixture for this lesson
    session.fixture = lesson.fixture
    session.reset()

    return {
        "lesson_title": lesson.title,
        "lesson_prompt": lesson.instructions,
        "total_lessons": len(track.lessons),
        "current_index": lesson_index
    }


@app.post("/api/session/{session_id}/stop")
def stop_session(session_id: str):
    if session_id in _sessions:
        _sessions[session_id].purge()
        del _sessions[session_id]
    return {"status": "ok"}


@app.get("/api/git/log")
def get_git_log(repo_path: str, skip: int = 0):
    """
    Fetch the git log for the given repository path.
    Enforces strict path canonicalization, .git directory validation, and subprocess hardening.
    """
    canonical_path = os.path.realpath(repo_path)

    # Path validation: must contain a .git directory or file
    git_dir = os.path.join(canonical_path, ".git")
    if not os.path.exists(git_dir):
        raise HTTPException(
            status_code=400,
            detail="Provided path is not a valid git repository (missing .git)")

    # Hardened subprocess call
    cmd = [
        "git",
        "log",
        "--all",
        "--format=%H%x00%P%x00%an%x00%aI%x00%d%x00%s",
        "--max-count=500",
        f"--skip={skip}"
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=canonical_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500,
                            detail="git executable not found on PATH.")
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Git log operation timed out (10s limit).")
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Git log failed: {e.stderr}")

    commits = []
    # Parse the null-byte delimited output
    for line in proc.stdout.strip("\n").split("\n"):
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) >= 6:
            commits.append({
                "hash": parts[0],
                "parents": parts[1].split() if parts[1] else [],
                "author": parts[2],
                "date": parts[3],
                "refs": parts[4].strip(" ()"),
                "message": parts[5]
            })

    return {"commits": commits, "repo": canonical_path}
