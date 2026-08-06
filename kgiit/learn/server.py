"""
kgiit.learn.server — FastAPI bridge for the Electron GUI.
"""
from __future__ import annotations

import subprocess

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kgiit.learn.curriculum import get_track
from kgiit.learn.ml.classifier import classify_mistake
from kgiit.learn.sandbox import SandboxSession, SandboxCommandError

app = FastAPI(title="kgiit GUI Bridge")

# In-memory session store for the bridge
# mapping: session_id -> SandboxSession
_sessions: dict[str, SandboxSession] = {}

class TrackStartRequest(BaseModel):
    track_id: str

class ExecuteRequest(BaseModel):
    command: str

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
def verify_lesson(session_id: str, req: dict):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    track_id = req.get("track_id")
    lesson_index = req.get("lesson_index", 0)
    last_command = req.get("last_command", "")
    exit_code = req.get("exit_code", 0)
    stdout = req.get("stdout", "")
    stderr = req.get("stderr", "")
    
    track = get_track(track_id)
    if not track or lesson_index >= len(track.lessons):
        raise HTTPException(status_code=400, detail="Invalid track or lesson")
        
    lesson = track.lessons[lesson_index]
    session = _sessions[session_id]
    
    # Mock a CompletedProcess for the verify signature
    mock_proc = subprocess.CompletedProcess(args=last_command, returncode=exit_code, stdout=stdout, stderr=stderr)
    
    result = lesson.verify(session, mock_proc)
    
    hint = None
    if not result.passed and last_command.startswith("git "):
        _, _, hint = classify_mistake(last_command, lesson.target_command, context=session.get_state())
        
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
