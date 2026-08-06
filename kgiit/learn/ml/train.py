"""
kgiit.learn.ml.train — Training script for the ML mistake classifier.

Usage:
    python -m kgiit.learn.ml.train

This script:
1. Generates synthetic training data (or loads existing CSV)
2. Builds a scikit-learn Pipeline:
   - ColumnTransformer: TF-IDF char n-grams on 'command' text
                        + numeric context features
   - RandomForestClassifier(n_estimators=200)
3. Trains on 80% of the data, evaluates on 20%
4. Prints accuracy + confusion matrix
5. Saves the trained pipeline to model.joblib

The trained model.joblib is committed to the repo so that install-time
training is NEVER required. This script is only needed if you want to
retrain after extending the dataset or adding new lessons.
"""

import sys
import time
from pathlib import Path

# Add project root to path if running as script
sys.path.insert(0, str(Path(__file__).parents[4]))

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    import joblib
except ImportError:
    from sklearn.externals import joblib

from kgiit.learn.ml.data_gen import (
    DATASET_PATH,
    generate_dataset,
    save_dataset,
)

MODEL_PATH = Path(__file__).parent / "model.joblib"
CONFIDENCE_THRESHOLD = 0.45  # Below this: fall back to rule-based hints


def load_or_generate_data():
    """Load dataset from CSV, generating it first if it doesn't exist."""
    if not DATASET_PATH.exists():
        print("[*] Generating training data (first run)...")
        rows = generate_dataset(n_per_class=35)
        count = save_dataset(rows)
        print(f"[+] Generated {count} rows -> {DATASET_PATH}")
    else:
        print(f"[*] Loading existing dataset from {DATASET_PATH}")

    import csv
    rows = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_pipeline() -> Pipeline:
    """
    Build the scikit-learn Pipeline.

    Architecture:
      ColumnTransformer:
        - TfidfVectorizer (char_wb, n-gram range 2-5) on 'command' text
          Good for typo detection — character n-grams are robust to
          small edit-distance errors.
        - StandardScaler on numeric features:
          edit_distance, flag_delta, arg_delta,
          context_has_staged, context_has_unstaged, context_is_init
      → RandomForestClassifier(n_estimators=200, random_state=42)
        Using 200 trees for stable predictions. RF is fast at inference
        (~5ms per prediction) well within the 50ms budget.
    """
    text_features = Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            max_features=5000,
            sublinear_tf=True,
        )),
    ])

    numeric_features = Pipeline([
        ("scaler", StandardScaler()),
    ])

    preprocessor = ColumnTransformer([
        ("text", text_features, "command"),
        ("numeric", numeric_features, [
            "edit_distance", "flag_delta", "arg_delta",
            "context_has_staged", "context_has_unstaged", "context_is_init",
        ]),
    ])

    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_split=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def prepare_X_y(rows):
    """Convert list-of-dicts into feature matrix and label vector."""
    import pandas as pd
    df = pd.DataFrame(rows)

    # Cast numeric columns
    for col in ["edit_distance", "flag_delta", "arg_delta",
                "context_has_staged", "context_has_unstaged", "context_is_init"]:
        df[col] = df[col].astype(float)

    X = df[["command", "edit_distance", "flag_delta", "arg_delta",
            "context_has_staged", "context_has_unstaged", "context_is_init"]]
    y = df["label"]
    return X, y


def train_and_evaluate():
    """Main training workflow. Returns the fitted pipeline."""
    t0 = time.time()

    # 1. Load data
    rows = load_or_generate_data()
    print(f"[*] Dataset size: {len(rows)} rows")

    X, y = prepare_X_y(rows)
    labels = sorted(y.unique())

    # 2. Train/test split (80/20, stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"[*] Train: {len(X_train)} rows | Test: {len(X_test)} rows")

    # 3. Build + train pipeline
    print("[*] Training RandomForestClassifier (200 trees)...")
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    # 4. Evaluate
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n{'='*60}")
    print(f"  Held-out Accuracy: {acc:.4f} ({acc*100:.1f}%)")
    print(f"{'='*60}\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred, labels=labels, zero_division=0))

    print("Confusion Matrix (rows=actual, cols=predicted):")
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    # Pretty print
    header = " " * 22 + "  ".join(f"{l[:6]:6s}" for l in labels)
    print(header)
    for i, label in enumerate(labels):
        row_str = f"{label:22s}  " + "  ".join(f"{cm[i,j]:6d}" for j in range(len(labels)))
        print(row_str)

    # 5. Timing
    elapsed = time.time() - t0
    print(f"\n[+] Training completed in {elapsed:.2f}s")

    # 6. Inference speed check
    sample = X_test.iloc[:10]
    t_inf = time.time()
    for _ in range(100):
        pipeline.predict_proba(sample)
    t_inf_avg = (time.time() - t_inf) / 100 * 1000 / 10  # ms per sample
    print(f"[+] Inference speed: ~{t_inf_avg:.1f}ms per prediction (target: <50ms)")

    return pipeline, acc


def save_model(pipeline, path: Path = MODEL_PATH) -> None:
    """Save the trained pipeline to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path)
    size_kb = path.stat().st_size / 1024
    print(f"[+] Model saved -> {path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    print("=" * 60)
    print("  kgiit ML Mistake Classifier — Training")
    print("=" * 60)
    pipeline, accuracy = train_and_evaluate()
    save_model(pipeline)
    print("\n[+] Done. model.joblib is ready for inference.")
    print("    Commit it to the repo so install-time training is never needed.")
