# KGiit — Agents and Skills Registry

This document is the authoritative registry of all custom agents and skills in the
KGiit system. It serves as the bridge between the formal specifications in
`.agents/skills/*/SKILL.md` and their Python implementations.

Every entry here is validated by `tests/test_skill_contract.py` — if an implementation
drifts from its spec, CI will catch it.

---

## Architecture Overview

```
.agents/
└── skills/
    ├── issue-triage/        ← Skill: classify a GitHub issue
    ├── duplicate-detector/  ← Skill: detect duplicate issues
    ├── priority-ranker/     ← Skill: rank classified issues by priority
    └── triage-summary/      ← Skill: generate triage narrative summary

kgiit/analyze/skills.py      ← Python implementations of all four skills above
kgiit/learn/ml/classifier.py ← ML Agent: classifies student Git command mistakes
```

---

## 🤖 Agents

### Agent 1: Issue Triage Agent

| Property | Value |
|----------|-------|
| **Name** | Issue Triage Agent |
| **Entry Point** | `kgiit analyze --repo <owner/repo>` |
| **Source** | `kgiit/analyze/` |
| **Mode** | Online (requires internet + optional `GITHUB_TOKEN`) |
| **LLM Dependency** | None — fully deterministic |

**What it does:**

The Issue Triage Agent is an automated, deterministic pipeline that analyzes open
GitHub issues for any public repository. It orchestrates four skills in sequence:

1. **Fetch** — Retrieves open issues via `kgiit/analyze/github_client.py` using the
   GitHub REST API (with optional auth token to bypass rate limits).
2. **Classify** — Runs each issue through the `issue-triage` skill to assign severity
   (HIGH/MEDIUM/LOW) and category label (bug, docs, perf, bug/auth, uncategorized).
3. **Detect Duplicates** — Runs the `duplicate-detector` skill using Jaccard similarity
   to identify potential duplicate issues.
4. **Rank** — Applies the `priority-ranker` skill to sort issues by severity + core
   flow impact.
5. **Summarize** — Generates a plain-text summary using the `triage-summary` skill.
6. **Report** — Formats all findings into a Rich-rendered terminal table via
   `kgiit/analyze/formatting.py`.

**Agent Rules File:** See `AGENTS.md` for full behavioral constraints.

**Example invocation:**
```bash
kgiit analyze --repo ShauryaVaid/kgiit
kgiit analyze --repo django/django --all-open
```

---

### Agent 2: ML Mistake Classifier (Learn Mode Agent)

| Property | Value |
|----------|-------|
| **Name** | ML Mistake Classifier |
| **Entry Point** | `kgiit learn` → interactive → any lesson |
| **Source** | `kgiit/learn/ml/classifier.py` |
| **Mode** | Offline (no internet, no API, no LLM) |
| **LLM Dependency** | None — scikit-learn model running locally |

**What it does:**

The ML Mistake Classifier is a locally-executing, pre-trained machine learning agent
that intercepts failed Git commands in the learning sandbox and classifies *why* the
student's command is wrong. It then selects a pre-written pedagogical hint template
and fills in the specifics.

**Classification Labels (12 total):**

| Label | Meaning |
|-------|---------|
| `TYPO` | Edit distance ≤ 3 from expected command |
| `WRONG_FLAG` | Correct subcommand but wrong flag (e.g., `-m` vs `-b`) |
| `MISSING_ARG` | Command shorter than expected — argument omitted |
| `EXTRA_ARG` | Command longer than expected — spurious argument added |
| `WRONG_SUBCOMMAND` | Wrong git subcommand entirely (e.g., `git add` vs `git commit`) |
| `WRONG_CONTEXT_STATE` | Command correct but repo isn't in the right state |
| `WRONG_ORDER` | Operation done out of sequence (e.g., commit before add) |
| `SYNTAX_ERROR` | Unparseable command |
| `DEPRECATED_USAGE` | Old-style syntax (e.g., `git checkout branch` vs `git switch`) |
| `PARTIALLY_CORRECT` | Close but not quite right |
| `CORRECT` | Command matches expected (used for short-circuit) |
| `UNKNOWN` | Fallback when nothing matches |

**Model Details:**
- Algorithm: Random Forest (scikit-learn pipeline)
- Training data: `kgiit/learn/ml/training_data.csv` (247KB, synthetic)
- Accuracy: 87.6% on held-out test set
- Inference time: 5.9ms average
- Confidence threshold: 0.45 (falls back to deterministic rules below this)
- Model artifact: `kgiit/learn/ml/model.joblib` (12.5MB)

**Fallback behavior:** When model confidence < 0.45, the agent falls back to a
deterministic rule-based classifier using Levenshtein edit distance and token analysis.

---

## 🛠️ Skills

### Skill 1: `issue-triage`

| Property | Value |
|----------|-------|
| **Spec file** | `.agents/skills/issue-triage/SKILL.md` |
| **Implementation** | `kgiit/analyze/skills.py` → `classify_issue()` |
| **Contract tests** | `tests/test_skill_contract.py::TestSkillContract::test_classify_issue_*` |

**Purpose:** Classifies a GitHub issue's title and body into a structured severity +
label + owner + reason output.

**Input:** A GitHub issue dict with keys `title`, `body`, `number`.

**Output schema:**
```json
{
  "issue_number": "#42",
  "severity": "HIGH | MEDIUM | LOW",
  "label": "bug/auth | perf | docs | bug | uncategorized",
  "owner": "@username or unassigned",
  "reason": "one-line explanation string"
}
```

**Severity rules:**
- `HIGH`: Contains crash, security, vulnerability, data loss, auth, payment, login, fatal
- `MEDIUM`: Contains slow, timeout, lag, performance, partial, error, fail, bug
- `LOW`: Everything else (typos, docs, cosmetic)

---

### Skill 2: `duplicate-detector`

| Property | Value |
|----------|-------|
| **Spec file** | `.agents/skills/duplicate-detector/SKILL.md` |
| **Implementation** | `kgiit/analyze/skills.py` → `detect_duplicates()` |
| **Contract tests** | `tests/test_skill_contract.py::TestSkillContract::test_detect_duplicates_*` |

**Purpose:** Identifies whether a given issue is a probable duplicate of any other
issue in the same set using Jaccard word-overlap similarity.

**Input:** A target issue dict + a list of all other issue dicts.

**Algorithm:** Jaccard similarity on word token sets.
- Score ≥ 0.60 → `is_duplicate: true, confidence: "high"`
- Score 0.35–0.59 → `is_duplicate: true, confidence: "medium"`
- Score < 0.35 → `is_duplicate: false, confidence: "low"`

**Output schema:**
```json
{
  "is_duplicate": true,
  "duplicate_of": "#17",
  "confidence": "high | medium | low"
}
```

---

### Skill 3: `priority-ranker`

| Property | Value |
|----------|-------|
| **Spec file** | `.agents/skills/priority-ranker/SKILL.md` |
| **Implementation** | `kgiit/analyze/skills.py` → `rank_priorities()` |
| **Contract tests** | `tests/test_skill_contract.py::TestSkillContract::test_rank_priorities_*` |

**Purpose:** Sorts a list of classified issues into a priority ranking using a
three-tier sort key: severity → core flow impact → issue number (older = higher priority).

**Input:** List of classified issue dicts (output of `classify_issue()`).

**Sort key:**
1. Severity: HIGH (0) > MEDIUM (1) > LOW (2)
2. Core flow: `bug/auth` or `bug/payment` labels rank above others
3. Issue number tiebreaker: older issues (lower number) rank higher

**Output schema:**
```json
[
  {
    "issue_number": "#1",
    "rank": 1,
    "reason": "Ranked #1 due to HIGH severity and 'bug/auth' category impact."
  }
]
```

---

### Skill 4: `triage-summary`

| Property | Value |
|----------|-------|
| **Spec file** | `.agents/skills/triage-summary/SKILL.md` |
| **Implementation** | `kgiit/analyze/skills.py` → `build_analyze_summary()` |
| **Contract tests** | `tests/test_skill_contract.py::TestSkillContract::test_build_analyze_summary_*` |

**Purpose:** Generates a concise plain-text executive summary of a triage run —
answering "what's the state of this repo's issues in two sentences?"

**Input:** List of classified issue dicts + optional list of duplicate detection results.

**Output:** A plain-text string (no JSON, no markdown, no bullets). Format:
`"<N> HIGH severity issues need attention, mostly in <label>. <M> issue(s) remain unassigned."`

**Constraints (per spec):**
- Must NOT return JSON, markdown, or bullet points
- Must mention HIGH count first if any exist
- Must mention unassigned count if any exist

---

## How Skills Are Tested

All four skills have their implementation verified against their formal SKILL.md specs
at every CI run via `tests/test_skill_contract.py`. The test suite:

1. Reads the SKILL.md file using `pathlib.Path`
2. Extracts the JSON schema block using regex
3. Parses all declared output keys
4. Calls the Python implementation with sample inputs
5. Asserts the returned dict/list contains all declared keys with correct types

This means **any drift between the spec and the implementation is caught before merge**,
not by a judge at demo time.

To run the contract tests manually:
```bash
pytest tests/test_skill_contract.py -v
```

---

## Adding a New Skill

1. Create `.agents/skills/<skill-name>/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: <one-line description>
   ---
   ```
2. Include an `## Output Requirement` section with a `\`\`\`json` schema block.
3. Implement the function in `kgiit/analyze/skills.py`.
4. Add contract tests in `tests/test_skill_contract.py`.
5. Register the skill in this document (`AGENTS_AND_SKILLS.md`).
6. Update `CHANGELOG.md`.
