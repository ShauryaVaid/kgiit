"""
kgiit.analyze.action_log — local, append-only audit trail for write-back actions.

Every attempted write-back (applied, declined, or failed) is recorded here as
one JSON object per line (JSONL), so a judge or teammate can `cat` the file
directly, or `kgiit log` for a formatted view. This module has no knowledge
of GitHub or of the confirmation UI — it only knows how to durably persist
and re-read structured entries, which keeps it trivially unit-testable and
safe to reuse for future write-back actions beyond labels.

Powered by the HowToAlgo ADLC philosophy: every decision is traceable,
every outcome auditable, every human approval provably on record.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = "kgiit-action-log.jsonl"


def log_action(
    *,
    action: str,
    status: str,
    repo: str,
    issue_number: int,
    confirmed_by: str,
    suggestion: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    log_path: str | Path = DEFAULT_LOG_PATH,
) -> dict[str, Any]:
    """
    Append one structured entry to the local audit log and return it.

    Parameters:
    - action: short machine name for the action type, e.g. "apply_label".
    - status: one of "applied", "declined", "failed", "skipped".
    - repo: "owner/name".
    - issue_number: the target GitHub issue number.
    - confirmed_by: who confirmed/declined this (verified GitHub login when
      available, e.g. "github:octocat", else an explicit or OS-derived name).
    - suggestion: the AI-suggested change that was in play.
    - result: what GitHub actually returned after a successful write.
    - error: human-readable failure reason, if status == "failed".
    - log_path: where to persist the JSONL file. Defaults to
      ./kgiit-action-log.jsonl in the current working directory, mirroring
      how analyze-report.md already defaults to the cwd.

    This function never raises on a *logging* failure being about the write-
    back itself — but if the log file genuinely cannot be written (disk full,
    permission denied), that exception is allowed to propagate, because a
    write-back that cannot be proven to have happened is not something this
    tool should silently swallow.
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "action": action,
        "status": status,
        "repo": repo,
        "issue_number": issue_number,
        "confirmed_by": confirmed_by,
        "suggestion": suggestion or {},
        "result": result or {},
        "error": error,
    }

    out_path = Path(log_path)
    if out_path.parent != Path("."):
        out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False))
        f.write("\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            # Best-effort durability; not fatal on filesystems that don't
            # support fsync (e.g. some network mounts).
            pass

    return entry


def read_log(log_path: str | Path = DEFAULT_LOG_PATH) -> list[dict[str, Any]]:
    """
    Read and parse every entry from the local audit log, oldest first.
    Returns an empty list if the log doesn't exist yet — no exception,
    since "no actions taken yet" is a normal, expected state.
    Malformed lines are skipped rather than raising, so a partially
    corrupted log still yields every readable entry.
    """
    p = Path(log_path)
    if not p.exists():
        return []

    entries: list[dict[str, Any]] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
