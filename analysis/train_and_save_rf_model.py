"""
Train and save an exploratory Random Forest model for later confidence scoring.

Reads the existing legacy feature dataset and writes NEW artifacts under outputs/ml.
Does not modify SMC strategy files or existing backtest results.

IMPORTANT:
- Legacy labels/timestamps have known alignment limitations.
- Scores are experimental, not calibrated real-world probabilities.
- Identifier fields (including trade_id) are excluded from model inputs.
- The model must be used later with the exact saved feature list and matching feature definitions.
"""

from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix
)
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "outputs" / "ml" / "gbpusd_m15_technical_features_legacy.csv"
OUTDIR = ROOT / "outputs" / "ml"
OUTDIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = OUTDIR / "rf_legacy_model.joblib"
FEATURES_PATH = OUTDIR / "rf_legacy_model_features.json"
METRICS_PATH = OUTDIR / "rf_legacy_saved_model_metrics.json"
REPORT_PATH = OUTDIR / "rf_legacy_saved_model_report.txt"

TARGET = "target_tp_first"
TIME_COL = "signal_time"

EXCLUDE_EXACT = {
    TARGET, "result", "rr", "signal_time", "feature_candle_time",
    "feature_status", "source_file", "entry", "sl", "tp",
    "legacy_result", "aligned_result", "target", "outcome",
    "trade_id", "id", "row_id", "index",
}
EXCLUDE_PREFIXES = ("target_", "result_", "outcome_", "label_", "trade_id")

def compute_metrics(y_true, y_pred, probabilities=None):
    m = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision_win": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_win": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_win": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "confusion_matrix_labels_0_1": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }
    m["roc_auc"] = (
        float(roc_auc_score(y_true, probabilities))
        if probabilities is not None and len(np.unique(y_true)) == 2
        else None
    )
    return m

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    if TARGET not in df.columns or TIME_COL not in df.columns:
        raise ValueError(f"Expected columns {TARGET!r} and {TIME_COL!r} in {DATA_PATH}")

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    df = df.dropna(subset=[TIME_COL, TARGET]).copy()
    df = df[df[TARGET].isin([0, 1])].sort_values(TIME_COL).reset_index(drop=True)

    excluded = set(EXCLUDE_EXACT)
    excluded.update(c for c in df.columns if c.startswith(EXCLUDE_PREFIXES))
    features = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not features:
        raise ValueError("No numeric feature columns found after excluding metadata/IDs.")

    X = df[features].replace([np.inf, -np.inf], np.nan)
    y = df[TARGET].astype(int)
    split_idx = int(len(df) * 0.70)
    if split_idx < 20 or len(df) - split_idx < 10:
        raise ValueError("Not enough rows for a chronological 70/30 split.")

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        raise ValueError("Train and test periods must each contain both labels.")

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=400,
            max_depth=4,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])
    baseline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", DummyClassifier(strategy="most_frequent")),
    ])

    model.fit(X_train, y_train)
    baseline.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, list(model.named_steps["model"].classes_).index(1)]
    base_pred = baseline.predict(X_test)

    rf_metrics = compute_metrics(y_test, pred, prob)
    baseline_metrics = compute_metrics(y_test, base_pred)

    # Refit on all available rows for later experimental scoring.
    # Evaluation metrics above remain from the chronological holdout before this refit.
    final_model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=400,
            max_depth=4,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])
    final_model.fit(X, y)
    joblib.dump(final_model, MODEL_PATH)

    feature_payload = {
        "target": TARGET,
        "time_column": TIME_COL,
        "features": features,
        "training_rows": int(len(df)),
        "training_start": str(df.iloc[0][TIME_COL]),
        "training_end": str(df.iloc[-1][TIME_COL]),
        "warning": "Legacy labels/timestamps are not validated; model scores are experimental.",
    }
    FEATURES_PATH.write_text(json.dumps(feature_payload, indent=2), encoding="utf-8")

    report_data = {
        "warning": "EXPLORATORY ONLY: legacy labels/timestamps have known alignment limitations.",
        "rows_used": int(len(df)),
        "features_used": features,
        "feature_count": len(features),
        "train_rows_for_holdout_evaluation": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "train_period": [str(df.iloc[0][TIME_COL]), str(df.iloc[split_idx - 1][TIME_COL])],
        "test_period": [str(df.iloc[split_idx][TIME_COL]), str(df.iloc[-1][TIME_COL])],
        "label_counts": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "holdout_random_forest_metrics": rf_metrics,
        "holdout_majority_baseline_metrics": baseline_metrics,
        "saved_final_model_fit": "refit on all legacy rows for experimental scoring",
        "model_file": str(MODEL_PATH),
        "feature_schema_file": str(FEATURES_PATH),
    }
    METRICS_PATH.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    lines = [
        "EXPLORATORY RANDOM FOREST — SAVED MODEL",
        "=" * 48,
        report_data["warning"],
        "",
        f"Rows used: {len(df)}",
        f"Features used: {len(features)}",
        f"Chronological holdout train/test: {len(X_train)}/{len(X_test)}",
        f"Holdout RF metrics: {json.dumps(rf_metrics)}",
        f"Holdout majority baseline: {json.dumps(baseline_metrics)}",
        "",
        "Saved artifacts:",
        f"Model: {MODEL_PATH}",
        f"Feature schema: {FEATURES_PATH}",
        f"Metrics: {METRICS_PATH}",
        "",
        "The saved model was refit on all 289 legacy rows for experimental scoring.",
        "Do not use its training fit as an unbiased performance estimate.",
        "Do not interpret its scores as calibrated real-world probabilities.",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
