---
name: priority-ranker
description: Ranks a list of classified GitHub issues by fix priority based on severity, core flow impact, and issue age. Use when asked to prioritize or rank GitHub issues.
---

# Priority Ranker

This skill provides instructions for ranking a list of pre-classified GitHub issues from highest to lowest resolution priority.

## Input

The input consists of an array of classified issues, where each entry contains:
- `issue_number`: Issue reference identifier (e.g., `"#142"`)
- `title`: Short summary title of the issue
- `severity`: Strictly `"HIGH"`, `"MEDIUM"`, or `"LOW"`
- `label`: Issue category label (e.g., `"bug/auth"`, `"perf"`, `"docs"`)

## Ranking Rules

Issues must be sorted in descending order of priority (1 being highest priority):

1. **Severity Grouping**: All `HIGH` severity issues come before `MEDIUM` severity issues, which come before `LOW` severity issues.
2. **Core Flow Impact**: Within the same severity level, issues affecting core flows (e.g., auth, payments, checkout, core features) rank higher than non-core issues.
3. **Age / Issue Number Tiebreaker**: If severity and core flow impact are identical, break ties using the issue number (lower issue number = older issue = ranks slightly higher).

## Output Requirement

- The output **MUST** be a strict JSON array only.
- Do **NOT** wrap the output in markdown codeblocks (e.g., do not use ` ```json ` or ` ``` `).
- Do **NOT** include any preamble, introduction, explanation, or trailing text outside of the JSON array.

### JSON Schema Structure

```json
[
  {
    "issue_number": "#142",
    "rank": 1,
    "reason": "Clear explanation of priority ranking rationale"
  }
]
```
