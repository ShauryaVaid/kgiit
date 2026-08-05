---
name: duplicate-detector
description: Compares a target GitHub issue against a list of existing open issues to detect duplicates based on semantic similarity. Use when checking for duplicate issues or performing issue deduplication.
---

# Duplicate Detector

This skill provides instructions for comparing a target GitHub issue against a list of existing open issues to determine if the target issue is a duplicate.

## Input

The input consists of:
1. **Target Issue**: Title and body text of the issue being evaluated.
2. **Existing Issues**: A list of open issues, where each entry includes the issue number (e.g., `#128`), title, and body text.

## Detection Rules

1. **Semantic Matching**: Compare issues based on the semantic similarity of the underlying core problem described, rather than relying on exact wording.
2. **Confidence Assignment**:
   - `high`: Same root cause and same feature area.
   - `medium`: Similar symptoms, but different area or unclear root cause.
   - `low`: Superficially similar but likely different bugs.
3. **Fallback / No Match**:
   - If no likely duplicate is found, set `is_duplicate` to `false`, `duplicate_of` to `null`, and `confidence` to `"low"`.

## Output Requirement

- The output **MUST** be strict JSON only.
- Do **NOT** wrap the output in markdown codeblocks (e.g., do not use ` ```json ` or ` ``` `).
- Do **NOT** include any preamble, introduction, explanation, or trailing text outside of the JSON object.

### JSON Schema Structure

```json
{
  "is_duplicate": boolean,
  "duplicate_of": "#128" | null,
  "confidence": "high" | "medium" | "low"
}
```
