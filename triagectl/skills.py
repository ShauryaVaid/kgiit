import re
from typing import Any, Dict, List, Optional


def classify_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a GitHub issue's title and body according to .agents/skills/issue-triage/SKILL.md.
    Returns dict with keys: severity, label, owner, reason.
    """
    title = issue.get("title", "") or ""
    body = issue.get("body", "") or ""
    combined_text = f"{title} {body}".lower()

    # 1. Severity Classification
    high_keywords = ["crash", "security", "vulnerability", "data loss", "auth", "payment", "login", "broken core", "fatal"]
    medium_keywords = ["slow", "timeout", "lag", "performance", "partial", "error", "fail", "bug"]
    
    if any(kw in combined_text for kw in high_keywords):
        severity = "HIGH"
        severity_reason = "Contains critical impact keywords (crashes, security, data loss, or core auth/payment flow)."
    elif any(kw in combined_text for kw in medium_keywords):
        severity = "MEDIUM"
        severity_reason = "Contains performance or non-fatal bug keywords."
    else:
        severity = "LOW"
        severity_reason = "Minor issue, cosmetic change, typo, or documentation update."

    # 2. Label Categorization
    if any(kw in combined_text for kw in ["login", "auth", "password"]):
        label = "bug/auth"
    elif any(kw in combined_text for kw in ["slow", "timeout", "lag", "perf", "latency"]):
        label = "perf"
    elif any(kw in combined_text for kw in ["readme", "docs", "guide", "typo", "wording", "copy", "documentation"]):
        label = "docs"
    elif any(kw in combined_text for kw in ["crash", "fix", "error", "fail", "broken", "bug"]):
        label = "bug"
    else:
        label = "uncategorized"

    # 3. Owner Detection
    owner_match = re.search(r"@([a-zA-Z0-9_-]+)", combined_text)
    if owner_match:
        owner = f"@{owner_match.group(1)}"
    else:
        owner = "unassigned"

    reason = f"{severity_reason} Categorized as '{label}'."

    return {
        "issue_number": f"#{issue.get('number', '')}",
        "severity": severity,
        "label": label,
        "owner": owner,
        "reason": reason,
    }


def detect_duplicates(target_issue: Dict[str, Any], existing_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare target issue against existing issues according to .agents/skills/duplicate-detector/SKILL.md.
    """
    target_num = target_issue.get("number")
    target_title = (target_issue.get("title") or "").lower()
    target_body = (target_issue.get("body") or "").lower()
    target_words = set(re.findall(r"\w+", f"{target_title} {target_body}"))

    best_match = None
    highest_score = 0.0

    for other in existing_issues:
        if other.get("number") == target_num:
            continue

        other_title = (other.get("title") or "").lower()
        other_body = (other.get("body") or "").lower()
        other_words = set(re.findall(r"\w+", f"{other_title} {other_body}"))

        if not target_words or not other_words:
            continue

        # Calculate word overlap Jaccard similarity score
        overlap = target_words.intersection(other_words)
        score = len(overlap) / float(len(target_words.union(other_words)))

        if score > highest_score:
            highest_score = score
            best_match = other

    if highest_score >= 0.6:
        return {
            "is_duplicate": True,
            "duplicate_of": f"#{best_match.get('number')}",
            "confidence": "high",
        }
    elif highest_score >= 0.35:
        return {
            "is_duplicate": True,
            "duplicate_of": f"#{best_match.get('number')}",
            "confidence": "medium",
        }
    else:
        return {
            "is_duplicate": False,
            "duplicate_of": None,
            "confidence": "low",
        }


def rank_priorities(classified_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank a list of classified issues according to .agents/skills/priority-ranker/SKILL.md rules.
    1. Severity: HIGH > MEDIUM > LOW
    2. Core Flow Impact: auth/login/payment > other
    3. Issue Number Tiebreaker (older issue = lower number = ranks higher)
    """
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def sort_key(item):
        sev_rank = severity_order.get(item.get("severity", "LOW"), 2)
        
        # Check core flow impact
        label = item.get("label", "").lower()
        core_flow = 0 if "auth" in label or "payment" in label else 1
        
        # Issue number tiebreaker
        raw_num = item.get("issue_number", "0").replace("#", "")
        num_val = int(raw_num) if raw_num.isdigit() else 999999
        
        return (sev_rank, core_flow, num_val)

    sorted_list = sorted(classified_issues, key=sort_key)
    
    ranked_output = []
    for rank_idx, item in enumerate(sorted_list, start=1):
        num_str = item.get("issue_number")
        sev = item.get("severity")
        lbl = item.get("label")
        reason = f"Ranked #{rank_idx} due to {sev} severity and '{lbl}' category impact."
        
        ranked_output.append({
            "issue_number": num_str,
            "rank": rank_idx,
            "reason": reason,
        })

    return ranked_output


def build_triage_summary(classified_issues: List[Dict[str, Any]], duplicates: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Generate a concise plain-text summary paragraph according to .agents/skills/triage-summary/SKILL.md.
    """
    if not classified_issues:
        return "No open issues evaluated for triage."

    high_count = sum(1 for item in classified_issues if item.get("severity") == "HIGH")
    unassigned_count = sum(1 for item in classified_issues if item.get("owner") == "unassigned")
    
    # Identify predominant category
    categories = [item.get("label") for item in classified_issues if item.get("label") and item.get("label") != "uncategorized"]
    if categories:
        most_common_cat = max(set(categories), key=categories.count)
        cat_str = f", mostly in {most_common_cat}"
    else:
        cat_str = ""

    dup_count = sum(1 for item in (duplicates or []) if item.get("is_duplicate"))
    dup_str = f" {dup_count} possible duplicate found." if dup_count > 0 else ""

    if high_count > 0:
        sentence1 = f"{high_count} HIGH severity issue{'s' if high_count > 1 else ''} need attention{cat_str}.{dup_str}"
    else:
        sentence1 = f"All issues are rated MEDIUM/LOW severity{cat_str}.{dup_str}"

    sentence2 = f" {unassigned_count} issue{'s remain' if unassigned_count != 1 else ' remains'} unassigned." if unassigned_count > 0 else " All issues are assigned."

    return f"{sentence1}{sentence2}".strip()
