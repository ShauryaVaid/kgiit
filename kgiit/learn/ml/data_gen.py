"""
kgiit.learn.ml.data_gen — Synthetic training data generator for the ML mistake classifier.

This module generates hundreds of labeled wrong-command variants per class per lesson,
creating a balanced few-thousand-row dataset for training the RandomForestClassifier.

LABEL TAXONOMY (12 classes):
  TYPO               — The command has a character-level typo
  WRONG_FLAG         — Wrong flag used (e.g. -M instead of -m)
  MISSING_ARG        — Required argument omitted
  EXTRA_ARG          — Unnecessary extra argument added
  WRONG_SUBCOMMAND   — Wrong git subcommand for the intent
  WRONG_CONTEXT_STATE — Right command, wrong repo state (e.g. commit before stage)
  WRONG_ORDER        — Correct commands but in wrong sequence
  SYNTAX_ERROR       — Malformed command that wouldn't parse
  DEPRECATED_USAGE   — Old syntax that no longer works
  PARTIALLY_CORRECT  — Correct intent, missing one required part
  CORRECT            — The command is fully correct
  UNKNOWN            — Can't be classified with confidence

HOW DATA IS GENERATED:
  For each lesson's correct command, we apply systematic mutation rules
  to generate labeled variants for each mistake class.
  The resulting CSV has columns: command, expected, label, context_has_staged,
  context_has_unstaged, context_is_init, edit_distance, flag_delta, arg_delta
"""
from __future__ import annotations

import csv
import random
import string
from dataclasses import dataclass
from pathlib import Path

# Output path for generated dataset
DATASET_PATH = Path(__file__).parent / "training_data.csv"

# Random seed for reproducibility
random.seed(42)

LABELS = [
    "TYPO",
    "WRONG_FLAG",
    "MISSING_ARG",
    "EXTRA_ARG",
    "WRONG_SUBCOMMAND",
    "WRONG_CONTEXT_STATE",
    "WRONG_ORDER",
    "SYNTAX_ERROR",
    "DEPRECATED_USAGE",
    "PARTIALLY_CORRECT",
    "CORRECT",
    "UNKNOWN",
]

# CSV columns
COLUMNS = [
    "command",
    "expected",
    "label",
    "context_has_staged",
    "context_has_unstaged",
    "context_is_init",
    "edit_distance",
    "flag_delta",
    "arg_delta",
]


def _edit_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return _edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            insertions = prev[j + 1] + 1
            deletions = curr[j] + 1
            substitutions = prev[j] + (ca != cb)
            curr.append(min(insertions, deletions, substitutions))
        prev = curr
    return prev[len(b)]


def _count_flags(cmd: str) -> int:
    """Count the number of flag tokens (starting with -) in a command."""
    return sum(1 for token in cmd.split() if token.startswith("-"))


def _count_args(cmd: str) -> int:
    """Count non-flag, non-subcommand tokens."""
    parts = cmd.split()
    if len(parts) <= 2:
        return 0
    return sum(1 for p in parts[2:] if not p.startswith("-"))


def _inject_typo(cmd: str) -> str:
    """Inject a single character-level typo into a random position."""
    if len(cmd) < 3:
        return cmd
    pos = random.randint(1, len(cmd) - 1)
    ops = ["substitute", "delete", "insert"]
    op = random.choice(ops)
    if op == "substitute":
        char = random.choice(string.ascii_lowercase + "-_")
        return cmd[:pos] + char + cmd[pos + 1:]
    elif op == "delete":
        return cmd[:pos] + cmd[pos + 1:]
    else:  # insert
        char = random.choice(string.ascii_lowercase)
        return cmd[:pos] + char + cmd[pos:]


def _make_row(command: str, expected: str, label: str, ctx: dict) -> dict:
    """Build a dataset row."""
    ed = _edit_distance(command, expected)
    flag_d = _count_flags(command) - _count_flags(expected)
    arg_d = _count_args(command) - _count_args(expected)
    return {
        "command": command,
        "expected": expected,
        "label": label,
        "context_has_staged": int(ctx.get("has_staged", 0)),
        "context_has_unstaged": int(ctx.get("has_unstaged", 0)),
        "context_is_init": int(ctx.get("is_init", 0)),
        "edit_distance": ed,
        "flag_delta": flag_d,
        "arg_delta": arg_d,
    }


# ---------------------------------------------------------------------------
# Per-lesson command specs
# ---------------------------------------------------------------------------

@dataclass
class CommandSpec:
    """Correct command + context for one lesson."""
    expected: str
    context: dict  # has_staged, has_unstaged, is_init
    wrong_subcommands: list[str]  # alternative wrong subcommands
    deprecated_forms: list[str]   # deprecated equivalents
    partial_forms: list[str]      # partially correct variants


COMMAND_SPECS = [
    CommandSpec(
        expected="git init",
        context={"has_staged": 0, "has_unstaged": 0, "is_init": 0},
        wrong_subcommands=[
            "git initialize",
            "git start",
            "git new",
            "git create",
            "git setup"],
        deprecated_forms=["git init ."],
        partial_forms=["init", "git"],
    ),
    CommandSpec(
        expected="git status",
        context={"has_staged": 0, "has_unstaged": 1, "is_init": 1},
        wrong_subcommands=[
            "git stat",
            "git state",
            "git show",
            "git info",
            "git check"],
        deprecated_forms=["git status -s"],
        partial_forms=["git", "status"],
    ),
    CommandSpec(
        expected="git add hello.txt",
        context={"has_staged": 0, "has_unstaged": 1, "is_init": 1},
        wrong_subcommands=[
            "git stage hello.txt",
            "git track hello.txt",
            "git include hello.txt"],
        deprecated_forms=["git add -u hello.txt"],
        partial_forms=["git add", "git add .txt"],
    ),
    CommandSpec(
        expected='git commit -m "Add hello.txt"',
        context={"has_staged": 1, "has_unstaged": 0, "is_init": 1},
        wrong_subcommands=[
            "git save",
            "git snapshot",
            "git record",
            "git push"],
        deprecated_forms=["git commit --message 'Add hello.txt'"],
        partial_forms=["git commit", "git commit -m"],
    ),
    CommandSpec(
        expected="git switch feature",
        context={"has_staged": 0, "has_unstaged": 0, "is_init": 1},
        wrong_subcommands=[
            "git change feature",
            "git move feature",
            "git go feature"],
        deprecated_forms=["git checkout feature"],
        partial_forms=["git switch", "git branch feature"],
    ),
    CommandSpec(
        expected="git merge feature",
        context={"has_staged": 0, "has_unstaged": 0, "is_init": 1},
        wrong_subcommands=[
            "git join feature",
            "git combine feature",
            "git pull feature"],
        deprecated_forms=["git merge --no-ff feature"],
        partial_forms=["git merge", "git branch -m feature"],
    ),
    # Additional specs for richer coverage
    CommandSpec(
        expected="git log --oneline",
        context={"has_staged": 0, "has_unstaged": 0, "is_init": 1},
        wrong_subcommands=["git history", "git show-log", "git commits"],
        deprecated_forms=["git log --pretty=oneline"],
        partial_forms=["git log"],
    ),
    CommandSpec(
        expected="git branch feature",
        context={"has_staged": 0, "has_unstaged": 0, "is_init": 1},
        wrong_subcommands=["git new feature", "git create feature"],
        deprecated_forms=["git branch -b feature"],
        partial_forms=["git branch"],
    ),
    CommandSpec(
        expected="git diff",
        context={"has_staged": 0, "has_unstaged": 1, "is_init": 1},
        wrong_subcommands=["git compare", "git changes", "git show-diff"],
        deprecated_forms=["git diff HEAD"],
        partial_forms=["diff"],
    ),
    CommandSpec(
        expected="git stash",
        context={"has_staged": 0, "has_unstaged": 1, "is_init": 1},
        wrong_subcommands=["git save-work", "git hide", "git shelve"],
        deprecated_forms=["git stash save"],
        partial_forms=["git sta"],
    ),
]


def _generate_for_spec(spec: CommandSpec, n_per_class: int = 30) -> list[dict]:
    """Generate n_per_class examples per label for one command spec."""
    rows = []
    expected = spec.expected
    ctx = spec.context

    # CORRECT
    for _ in range(n_per_class):
        rows.append(_make_row(expected, expected, "CORRECT", ctx))

    # TYPO — inject 1-2 typos
    for _ in range(n_per_class):
        typo_cmd = _inject_typo(expected)
        if random.random() > 0.5:
            typo_cmd = _inject_typo(typo_cmd)
        rows.append(_make_row(typo_cmd, expected, "TYPO", ctx))

    # WRONG_FLAG — swap or corrupt a flag
    flag_variants = []
    parts = expected.split()
    for i, p in enumerate(parts):
        if p.startswith("-"):
            # Swap the flag character
            bad_flag = "-" + \
                random.choice("abcdefghijklnopqrstvwxyzABCDEFMNOPQRSTVWXYZ")
            bad_parts = parts[:i] + [bad_flag] + parts[i + 1:]
            flag_variants.append(" ".join(bad_parts))
    if not flag_variants:
        # Add a spurious flag
        flag_variants = [
            expected + " --verbose",
            expected + " -v",
            expected + " -f",
            expected + " --dry-run"]
    for i in range(n_per_class):
        rows.append(_make_row(flag_variants[i % len(
            flag_variants)], expected, "WRONG_FLAG", ctx))

    # MISSING_ARG — remove trailing argument
    parts = expected.split()
    if len(parts) > 2:
        missing_arg = " ".join(parts[:-1])
    else:
        missing_arg = parts[0]
    for _ in range(n_per_class):
        rows.append(_make_row(missing_arg, expected, "MISSING_ARG", ctx))

    # EXTRA_ARG — add a spurious extra argument
    extra_args = [
        "--verbose",
        "--dry-run",
        "--all",
        "extra_file.txt",
        "--force",
        "-v"]
    for i in range(n_per_class):
        extra = expected + " " + random.choice(extra_args)
        rows.append(_make_row(extra, expected, "EXTRA_ARG", ctx))

    # WRONG_SUBCOMMAND
    for i in range(n_per_class):
        cmd = spec.wrong_subcommands[i % len(spec.wrong_subcommands)]
        rows.append(_make_row(cmd, expected, "WRONG_SUBCOMMAND", ctx))

    # WRONG_CONTEXT_STATE — right command, wrong context flags
    bad_ctx = {k: (1 - v) if isinstance(v, int) else v for k, v in ctx.items()}
    for _ in range(n_per_class):
        rows.append(
            _make_row(
                expected,
                expected,
                "WRONG_CONTEXT_STATE",
                bad_ctx))

    # WRONG_ORDER — e.g. "commit" before "add"
    wrong_order_cmds = [
        "git commit -m 'message'",
        "git push origin main",
        "git merge main",
        "git switch feature",
    ]
    for i in range(n_per_class):
        cmd = wrong_order_cmds[i % len(wrong_order_cmds)]
        rows.append(_make_row(cmd, expected, "WRONG_ORDER", ctx))

    # SYNTAX_ERROR — clearly malformed
    syntax_errors = [
        "git " + expected.replace("git ", "").replace(" ", "="),
        "git --" + expected.replace("git ", ""),
        expected.replace(" ", ""),
        "git" + expected,
        "$ " + expected,
        expected.replace('"', "").replace("'", ""),
    ]
    for i in range(n_per_class):
        rows.append(_make_row(syntax_errors[i % len(
            syntax_errors)], expected, "SYNTAX_ERROR", ctx))

    # DEPRECATED_USAGE
    for i in range(n_per_class):
        dep = spec.deprecated_forms[i % len(spec.deprecated_forms)]
        rows.append(_make_row(dep, expected, "DEPRECATED_USAGE", ctx))

    # PARTIALLY_CORRECT
    for i in range(n_per_class):
        partial = spec.partial_forms[i % len(spec.partial_forms)]
        rows.append(_make_row(partial, expected, "PARTIALLY_CORRECT", ctx))

    # UNKNOWN — completely unrelated commands
    unknowns = [
        "ls -la", "pwd", "cd ..", "mkdir test", "rm -rf test",
        "cat hello.txt", "echo hello", "python script.py",
        "npm install", "pip install requests",
    ]
    for i in range(n_per_class):
        rows.append(_make_row(unknowns[i %
                                       len(unknowns)], expected, "UNKNOWN", ctx))

    return rows


def generate_dataset(n_per_class: int = 30) -> list[dict]:
    """Generate the full training dataset from all command specs."""
    all_rows = []
    for spec in COMMAND_SPECS:
        rows = _generate_for_spec(spec, n_per_class=n_per_class)
        all_rows.extend(rows)

    # Shuffle for good measure
    random.shuffle(all_rows)
    return all_rows


def save_dataset(rows: list[dict], output_path: Path = DATASET_PATH) -> int:
    """Save dataset rows to CSV. Returns count of rows written."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    print("[*] Generating synthetic training data...")
    rows = generate_dataset(n_per_class=35)
    count = save_dataset(rows)
    print(f"[+] Generated {count} rows -> {DATASET_PATH}")
    # Label distribution
    from collections import Counter
    dist = Counter(r["label"] for r in rows)
    for label, cnt in sorted(dist.items()):
        print(f"    {label:25s} {cnt:4d} rows")
