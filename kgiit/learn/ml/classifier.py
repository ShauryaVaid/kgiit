"""
kgiit.learn.ml.classifier — Inference wrapper for the ML mistake classifier.

This module loads the pre-trained model.joblib and exposes a single
predict() function used by the TUI to classify wrong commands and
select the right hint template.

DESIGN PRINCIPLES:
  - No LLM, no external API, fully offline
  - Inference target: <50ms per prediction
  - Below CONFIDENCE_THRESHOLD (0.45): fall back to deterministic rule-based hint
  - Hint text is never generated at runtime — the model selects a pre-written
    template and fills slots with {typed} / {expected} values

LOW-CONFIDENCE FALLBACK:
  When the model's top probability is below the threshold, we fall back to
  a deterministic rule-based classifier that checks simple heuristics:
    1. Edit distance < 3 → TYPO
    2. Same subcommand, different flags → WRONG_FLAG
    3. Shorter than expected → MISSING_ARG
    4. Longer than expected (extra tokens) → EXTRA_ARG
    5. Completely different subcommand → WRONG_SUBCOMMAND
    6. Otherwise → PARTIALLY_CORRECT
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "model.joblib"
CONFIDENCE_THRESHOLD = 0.45

# All valid mistake class labels
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

# ---------------------------------------------------------------------------
# Hint templates (pre-written — model only selects template + fills slots)
# ---------------------------------------------------------------------------

HINT_TEMPLATES: dict[str, str] = {
    "TYPO": (
        "Looks like a typo! You typed:\n"
        "  {typed}\n\n"
        "Did you mean:\n"
        "  {expected}\n\n"
        "Tip: git commands use all-lowercase subcommands."
    ),
    "WRONG_FLAG": (
        "The flag you used doesn't work here.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Check the flag carefully. Common git flags:\n"
        "  -m  (commit message)  -b  (create branch)  -u  (set upstream)"
    ),
    "MISSING_ARG": (
        "You're missing a required argument.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Git needs more information. Check what argument is missing."
    ),
    "EXTRA_ARG": (
        "Your command has an extra argument that git doesn't expect here.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Try removing the extra part."
    ),
    "WRONG_SUBCOMMAND": (
        "That's not the right git subcommand for what you're trying to do.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Common git subcommands: init, status, add, commit, branch, switch, merge, log, diff"
    ),
    "WRONG_CONTEXT_STATE": (
        "The command is right, but the repository isn't in the right state for it.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Hint: check git status first to see the current state of your repo."
    ),
    "WRONG_ORDER": (
        "You're doing things in the wrong order.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Git workflow for saving changes:\n"
        "  1. git add <file>   (stage)\n"
        "  2. git commit -m '...'  (commit)"
    ),
    "SYNTAX_ERROR": (
        "Your command has a syntax error that git can't parse.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Check spacing, quotes, and special characters."
    ),
    "DEPRECATED_USAGE": (
        "That syntax used to work in older git versions but is deprecated.\n\n"
        "You typed:    {typed}\n"
        "Modern way:   {expected}\n\n"
        "git switch replaces git checkout for branch operations (git 2.23+)."
    ),
    "PARTIALLY_CORRECT": (
        "You're on the right track, but the command isn't quite complete.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Look at the expected command carefully — what's different?"
    ),
    "CORRECT": (
        "That looks correct! If the command failed, check:\n"
        "  • Is git installed? (git --version)\n"
        "  • Are you in the right directory?\n"
        "  • Is there an error message from git itself?"
    ),
    "UNKNOWN": (
        "I'm not sure why that command didn't work.\n\n"
        "You typed:    {typed}\n"
        "Expected:     {expected}\n\n"
        "Try running: git --help   or   git <subcommand> --help"
    ),
}


def _edit_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance."""
    if len(a) < len(b):
        return _edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(
                min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[len(b)]


def _count_flags(cmd: str) -> int:
    return sum(1 for t in cmd.split() if t.startswith("-"))


def _rule_based_classify(typed: str, expected: str) -> str:
    """
    Deterministic fallback classifier using simple heuristics.
    Used when ML confidence is below CONFIDENCE_THRESHOLD.
    """
    ed = _edit_distance(typed, expected)
    typed_parts = typed.split()
    expected_parts = expected.split()

    # Very close? → TYPO
    if ed <= 3 and len(typed_parts) > 0 and len(expected_parts) > 0:
        return "TYPO"

    # Same first token (git) but different subcommand?
    if (len(typed_parts) >= 2 and len(expected_parts) >= 2
            and typed_parts[0] == expected_parts[0]
            and typed_parts[1] != expected_parts[1]):
        return "WRONG_SUBCOMMAND"

    # Same subcommand, different flags?
    if (len(typed_parts) >= 2 and len(expected_parts) >= 2
            and typed_parts[1] == expected_parts[1]
            and _count_flags(typed) != _count_flags(expected)):
        return "WRONG_FLAG"

    # Shorter → MISSING_ARG
    if len(typed_parts) < len(expected_parts):
        return "MISSING_ARG"

    # Longer → EXTRA_ARG
    if len(typed_parts) > len(expected_parts):
        return "EXTRA_ARG"

    return "PARTIALLY_CORRECT"


def _build_feature_row(typed: str, expected: str,
                       context: dict[str, Any]) -> dict[str, Any]:
    """Build a single feature row for model inference."""
    ed = _edit_distance(typed, expected)
    flag_d = _count_flags(typed) - _count_flags(expected)
    arg_d = (len([t for t in typed.split()[2:] if not t.startswith("-")])
             - len([t for t in expected.split()[2:] if not t.startswith("-")]))
    return {
        "command": typed,
        "edit_distance": float(ed),
        "flag_delta": float(flag_d),
        "arg_delta": float(arg_d),
        "context_has_staged": float(int(context.get("has_staged", 0))),
        "context_has_unstaged": float(int(context.get("has_unstaged", 0))),
        "context_is_init": float(int(context.get("is_init", 1))),
    }


class MistakeClassifier:
    """
    Wrapper around the pre-trained scikit-learn pipeline.

    Loads model.joblib lazily on first call to predict().
    Falls back to rule-based classification when:
      - model.joblib doesn't exist (e.g. in CI without model)
      - ML confidence is below CONFIDENCE_THRESHOLD
    """

    _instance: MistakeClassifier | None = None
    _pipeline = None
    _model_loaded: bool = False
    _model_available: bool = False

    def __init__(self):
        self._load_model()

    def _load_model(self) -> None:
        """Lazily load the model from disk."""
        if not MODEL_PATH.exists():
            logger.warning(
                f"model.joblib not found at {MODEL_PATH}. "
                "Using rule-based fallback. Run 'python -m kgiit.learn.ml.train' to train."
            )
            self._model_available = False
            return
        try:
            import joblib
            self._pipeline = joblib.load(MODEL_PATH)
            self._model_available = True
            logger.info(f"Loaded ML classifier from {MODEL_PATH}")
        except Exception as e:
            logger.warning(
                f"Failed to load model: {e}. Using rule-based fallback.")
            self._model_available = False

    def predict(
        self,
        typed: str,
        expected: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, float, str]:
        """
        Classify why a command is wrong and return the appropriate hint.

        Args:
            typed: The command the user actually typed
            expected: The command the lesson expects
            context: Dict with keys has_staged, has_unstaged, is_init (all bool/int)

        Returns:
            Tuple of (label, confidence, hint_text)
            - label: one of the 12 LABELS
            - confidence: float 0.0–1.0
            - hint_text: pre-written hint string with {typed}/{expected} filled in
        """
        if context is None:
            context = {}

        # If command is correct, short-circuit
        if typed.strip() == expected.strip():
            return "CORRECT", 1.0, HINT_TEMPLATES["CORRECT"].format(
                typed=typed, expected=expected
            )

        label = None
        confidence = 0.0

        if self._model_available and self._pipeline is not None:
            try:
                import pandas as pd
                row = _build_feature_row(typed, expected, context)
                df = pd.DataFrame([row])
                proba = self._pipeline.predict_proba(df)[0]
                classes = self._pipeline.classes_
                best_idx = proba.argmax()
                confidence = float(proba[best_idx])
                ml_label = classes[best_idx]

                if confidence >= CONFIDENCE_THRESHOLD:
                    label = ml_label
                else:
                    logger.debug(
                        f"ML confidence {confidence:.2f} below threshold {CONFIDENCE_THRESHOLD}. "
                        f"Falling back to rules. (ML predicted: {ml_label})"
                    )
            except Exception as e:
                logger.warning(
                    f"ML inference error: {e}. Using rule-based fallback.")

        # Fall back to rule-based
        if label is None:
            label = _rule_based_classify(typed, expected)
            confidence = 0.0  # Indicate rule-based

        # Get hint template and fill slots
        template = HINT_TEMPLATES.get(label, HINT_TEMPLATES["UNKNOWN"])
        hint_text = template.format(typed=typed, expected=expected)

        return label, confidence, hint_text


# Singleton — one classifier instance loaded at module level
_classifier: MistakeClassifier | None = None


def get_classifier() -> MistakeClassifier:
    """Get (or lazily create) the global classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = MistakeClassifier()
    return _classifier


def classify_mistake(
    typed: str,
    expected: str,
    context: dict[str, Any] | None = None,
) -> tuple[str, float, str]:
    """
    Convenience function: classify a mistake and return (label, confidence, hint).

    This is the primary entry point called by the TUI when a user's command
    doesn't pass the deterministic verification check.
    """
    return get_classifier().predict(typed, expected, context)
