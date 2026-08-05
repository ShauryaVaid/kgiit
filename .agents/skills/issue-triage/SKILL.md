---
name: issue-triage
description: Classifies a GitHub issue's title and body text into severity, label, owner, and reason. Use when asked to triage, classify, or label GitHub issues.
---

# Issue Triage

This skill provides instructions for analyzing a GitHub issue's title and body text and outputting a structured JSON classification.

## Input

The input consists of a GitHub issue title and body text.

## Classification Rules

1. **severity**: Must be strictly one of `HIGH`, `MEDIUM`, or `LOW`.
   - `HIGH`: Crashes, security issues, data loss, or breaks a core flow (auth, payments, etc.).
   - `MEDIUM`: Performance issues or partial breakage affecting some users.
   - `LOW`: Typos, cosmetic issues, or documentation.

2. **label**: Short category string determined using keyword matching.
   - Example keyword mappings:
     - Keywords like `"login"`, `"auth"`, `"password"` → `bug/auth`
     - Keywords like `"slow"`, `"timeout"`, `"lag"` → `perf`
     - Keywords like `"readme"`, `"docs"`, `"guide"` → `docs`
     - Keywords like `"typo"`, `"wording"`, `"copy"`, `"text content"`, `"documentation"` → `docs`
   - If there is no confident label match, return `"uncategorized"`.

3. **owner**:
   - Return a `@username` guess only if a clear owner signal is present in the issue context.
   - If no owner signal is available, return `"unassigned"` instead of guessing.

4. **reason**: A clear, concise one-line explanation of the classification rationale.

## Output Requirement

- The output **MUST** be strict JSON only.
- Do **NOT** wrap the output in markdown codeblocks (e.g., do not use ` ```json ` or ` ``` `).
- Do **NOT** include any preamble, introduction, explanation, or trailing text outside of the JSON object.

### JSON Schema Structure

```json
{
  "severity": "HIGH | MEDIUM | LOW",
  "label": "short string",
  "owner": "@username or unassigned",
  "reason": "one-line explanation"
}
```
