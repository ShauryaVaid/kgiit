"""
kgiit.analyze.writeback — confirmed write-back of AI suggestions to real issues.

This module is the seam between "AI suggests" (kgiit.analyze.skills) and
"human decides, then it happens for real" (kgiit.analyze.github_client). It
deliberately contains ZERO input()/Confirm.ask() prompting — that lives in
the CLI layer — so this module is:
  1. Fully unit-testable without simulating a terminal.
  2. Reusable from the Electron GUI or a future non-interactive approval
     queue without rewriting the write-back logic itself.
  3. A single, auditable place where "what does it mean to apply a
     suggestion" is defined once.

The single highest-risk action in kgiit is this one: writing an AI-suggested
label onto a real, third-party-visible GitHub issue. Everything below exists
to make sure that only ever happens after an explicit human confirmation,
and that there is always a durable local record of who confirmed it, what
was applied, and when — whether it succeeded or failed.

Architecture aligned with HowToAlgo ADLC: AI suggests → Human decides →
System acts → Every outcome logged. The human is never bypassed.
"""
from __future__ import annotations

import getpass
from typing import Any

from kgiit.analyze.action_log import DEFAULT_LOG_PATH, log_action
from kgiit.analyze.github_client import GitHubAPIError, GitHubClient

ACTION_APPLY_LABEL = "apply_label"


def build_suggestion_labels(classification: dict[str, Any]) -> list[str]:
    """
    Translate a classify_issue() result into the concrete GitHub labels a
    write-back would apply: the category label plus a priority:<severity>
    label. Returns [] if the classifier produced nothing actionable.
    """
    labels: list[str] = []
    label = classification.get("label")
    severity = classification.get("severity")

    if label and label != "uncategorized":
        labels.append(label)
    if severity:
        labels.append(f"priority:{severity.lower()}")

    return labels


def resolve_identity(client: GitHubClient, fallback: str | None = None) -> str:
    """
    Determine who is confirming this write-back, preferring a verified
    identity over a self-reported one:
      1. The GitHub login the configured token actually authenticates as
         (proven by GitHub itself, not just typed in).
      2. An explicit --confirmed-by value the operator supplied.
      3. The local OS username, as a last resort.
    Never raises — identity resolution failing is not a reason to block
    the rest of the flow; it degrades gracefully to a weaker attribution.
    """
    try:
        user = client.get_authenticated_user()
        login = user.get("login") if isinstance(user, dict) else None
        if login:
            return f"github:{login}"
    except GitHubAPIError:
        pass

    if fallback:
        return fallback

    try:
        return f"os:{getpass.getuser()}"
    except Exception:
        return "unknown"


def decline_suggestion(
    *,
    owner: str,
    repo: str,
    issue_number: int,
    classification: dict[str, Any],
    confirmed_by: str,
    log_path: str = DEFAULT_LOG_PATH,
) -> dict[str, Any]:
    """
    Record that a suggested write-back was explicitly declined. Nothing is
    sent to GitHub. Logged so "decline-then-confirm" is verifiable end to
    end: a reviewer can see the decline, then the later apply, in the same
    audit trail.
    """
    entry = log_action(
        action=ACTION_APPLY_LABEL,
        status="declined",
        repo=f"{owner}/{repo}",
        issue_number=issue_number,
        confirmed_by=confirmed_by,
        suggestion={
            "labels_proposed": build_suggestion_labels(classification),
            **classification,
        },
        log_path=log_path,
    )
    return {"ok": False, "applied": False, "entry": entry}


def apply_suggestion(
    client: GitHubClient,
    *,
    owner: str,
    repo: str,
    issue_number: int,
    classification: dict[str, Any],
    confirmed_by: str,
    log_path: str = DEFAULT_LOG_PATH,
) -> dict[str, Any]:
    """
    Apply a single classified suggestion to a real GitHub issue, and record
    the outcome — success or failure — in the local audit log.

    This function never raises. A GitHub write failure (bad token, no
    permission, issue not found, GitHub unreachable) is caught, logged with
    status="failed" and the error message, and returned as a structured
    result — so a network blip during a live demo degrades to a clear,
    logged failure message instead of a crash.
    """
    repo_full = f"{owner}/{repo}"
    labels_to_apply = build_suggestion_labels(classification)

    if not labels_to_apply:
        entry = log_action(
            action=ACTION_APPLY_LABEL,
            status="skipped",
            repo=repo_full,
            issue_number=issue_number,
            confirmed_by=confirmed_by,
            suggestion=classification,
            error="Classifier produced no actionable label for this issue.",
            log_path=log_path,
        )
        return {"ok": False, "applied": False, "entry": entry}

    try:
        labels_now_on_issue = client.add_labels(
            owner, repo, issue_number, labels_to_apply)
        entry = log_action(
            action=ACTION_APPLY_LABEL,
            status="applied",
            repo=repo_full,
            issue_number=issue_number,
            confirmed_by=confirmed_by,
            suggestion={
                "labels_applied": labels_to_apply,
                **classification,
            },
            result={"labels_now_on_issue": labels_now_on_issue},
            log_path=log_path,
        )
        return {
            "ok": True,
            "applied": True,
            "entry": entry,
            "labels_now_on_issue": labels_now_on_issue,
        }
    except GitHubAPIError as exc:
        entry = log_action(
            action=ACTION_APPLY_LABEL,
            status="failed",
            repo=repo_full,
            issue_number=issue_number,
            confirmed_by=confirmed_by,
            suggestion={
                "labels_attempted": labels_to_apply,
                **classification,
            },
            error=str(exc),
            log_path=log_path,
        )
        return {"ok": False, "applied": False, "entry": entry, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        # Anything truly unexpected still gets logged and reported cleanly
        # rather than propagating a raw traceback out of a live demo.
        entry = log_action(
            action=ACTION_APPLY_LABEL,
            status="failed",
            repo=repo_full,
            issue_number=issue_number,
            confirmed_by=confirmed_by,
            suggestion={
                "labels_attempted": labels_to_apply,
                **classification,
            },
            error=f"Unexpected error: {exc}",
            log_path=log_path,
        )
        return {"ok": False, "applied": False, "entry": entry, "error": str(exc)}
