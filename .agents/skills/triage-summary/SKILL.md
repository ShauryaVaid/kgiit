---
name: triage-summary
description: Generates a concise plain-text summary paragraph of issue triage results for CLI output. Use when asked to summarize triage findings or CLI results.
---

# Triage Summary

This skill provides instructions for generating a concise, human-readable plain-text summary of issue triage results suitable for CLI output.

## Input

The input consists of a list of classified issues, where each entry contains metadata such as:
- `severity`: `"HIGH"`, `"MEDIUM"`, or `"LOW"`
- `label`: Category label (e.g., `"bug/auth"`, `"perf"`, `"docs"`)
- `owner`: Assigned user (e.g., `"@username"`) or `"unassigned"`
- Optional duplicate status or total count context

## Summary Rules

Generate a single plain-text paragraph following these rules:

1. **Highlight HIGH Severity**: If any `HIGH` severity issues exist, mention their count first.
2. **Category Pattern**: Highlight the most frequent label or category if a predominant pattern exists.
3. **Assignment Status**: Note if any issues remain unassigned.
4. **Length and Format**:
   - Maximum 2-3 sentences.
   - Must be a single plain-text paragraph.
   - Do **NOT** use bullet points, markdown formatting, or JSON.

## Output Example

`3 HIGH severity issues need attention, mostly in auth. 1 possible duplicate found. 2 issues remain unassigned.`
