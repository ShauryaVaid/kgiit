import os
import subprocess
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from kgiit.learn.server import app

# Create a test client with a dummy auth token to bypass the Depends check if set
client = TestClient(app)
client.headers.update({"X-Auth-Token": "dummy_token_for_test"})

def test_missing_git_repo(tmp_path):
    """Test that querying a non-repo path returns 400."""
    response = client.get(f"/api/git/log?repo_path={tmp_path}")
    assert response.status_code == 400
    assert "missing .git" in response.json()["detail"]

def test_path_traversal_escapes(tmp_path):
    """Test that malicious traversal does not bypass validation."""
    # Ensure even if they pass something like ../../../etc it gets canonicalized 
    # and if it doesn't have .git, it fails.
    response = client.get("/api/git/log?repo_path=../../../../etc")
    assert response.status_code == 400

@patch("subprocess.run")
def test_git_missing(mock_run, tmp_path):
    """Test mocking FileNotFoundError for missing git binary."""
    # Create a fake .git dir to pass the first validation step
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    
    mock_run.side_effect = FileNotFoundError()
    
    response = client.get(f"/api/git/log?repo_path={tmp_path}")
    assert response.status_code == 500
    assert "git executable not found" in response.json()["detail"]
    mock_run.assert_called_once()

@patch("subprocess.run")
def test_subprocess_timeout(mock_run, tmp_path):
    """Test that subprocess.TimeoutExpired returns 504."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git", "log"], timeout=10)
    
    response = client.get(f"/api/git/log?repo_path={tmp_path}")
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]

@patch("subprocess.run")
def test_git_error(mock_run, tmp_path):
    """Test that git command failure returns 500."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    
    mock_run.side_effect = subprocess.CalledProcessError(returncode=128, cmd=["git", "log"], stderr="fatal: bad default revision 'HEAD'")
    
    response = client.get(f"/api/git/log?repo_path={tmp_path}")
    assert response.status_code == 500
    assert "fatal: bad default revision" in response.json()["detail"]

@patch("subprocess.run")
def test_successful_log(mock_run, tmp_path):
    """Test successful parsing of the null-byte delimited format."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    
    fake_output = (
        "hash1\x00parent1\x00Author Name\x002026-08-07T12:00:00Z\x00HEAD -> main\x00Initial commit\n"
        "hash2\x00\x00Another Author\x002026-08-06T12:00:00Z\x00\x00Older commit"
    )
    mock_run.return_value = subprocess.CompletedProcess(args=["git"], returncode=0, stdout=fake_output, stderr="")
    
    response = client.get(f"/api/git/log?repo_path={tmp_path}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["commits"]) == 2
    
    assert data["commits"][0]["hash"] == "hash1"
    assert data["commits"][0]["parents"] == ["parent1"]
    assert data["commits"][0]["refs"] == "HEAD -> main"
    
    assert data["commits"][1]["hash"] == "hash2"
    assert data["commits"][1]["parents"] == []
    assert data["commits"][1]["refs"] == ""
