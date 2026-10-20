"""
Exploratory Random Forest baseline for QuantEdge's legacy ML dataset.

This script:
- Does NOT modify SMC strategy files or existing backtest outputs.
- Uses a chronological 70/30 train/test split.
- Compares Random Forest with a majority-class baseline.
- Saves metrics and test predictions to new files under outputs/ml.

WARNING:
The source labels come from backtest_results_v1.csv, whose timestamps were flagged
by the timing audit. Treat all results as exploratory, not validated predictive
performance. Do not use these metrics as proof of profitability.
"""

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "outputs" / "ml" / "gbpusd_m15_technical_features_legacy.csv"
OUTDIR = ROOT / "outputs" / "ml"
OUTDIR.mkdir(parents=True, exist_ok=True)

PREDICTIONS_PATH = OUTDIR / "rf_legacy_test_predictions.csv"
METRICS_PATH = OUTDIR / "rf_legacy_metrics.json"
REPORT_PATH = OUTDIR / "rf_legacy_report.txt"

TARGET = "target_tp_first"
TIME_COL = "signal_time"

# Explicitly exclude labels, outcomes, identifiers, prices, and other post-trade
# fields so the model does not directly receive the answer or trade result.
EXCLUDE_EXACT = {
    TARGET, "result", "rr", "signal_time", "feature_candle_time",
    "feature_status", "source_file", "entry", "sl", "tp",
    "legacy_result", "aligned_result", "target", "outcome",
}
EXCLUDE_PREFIXES = ("target_", "result_", "outcome_", "label_")

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}\n"
            "Run analysis/prepare_technical_dataset.py first."
        )

    df = pd.read_csv(DATA_PATH)
    required = {TARGET, TIME_COL}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    df = df.dropna(subset=[TIME_COL, TARGET]).copy()
    df = df[df[TARGET].isin([0, 1])].sort_values(TIME_COL).reset_index(drop=True)

    excluded = set(EXCLUDE_EXACT)
    excluded.update(c for c in df.columns if c.startswith(EXCLUDE_PREFIXES))
    candidate_cols = [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]
    # Keep numeric feature columns only; nonnumeric metadata is not model input.
    if not candidate_cols:
        raise ValueError("No numeric feature columns found after excluding labels/metadata.")

    X = df[candidate_cols].replace([np.inf, -np.inf], np.nan)
    y = df[TARGET].astype(int)

    # Chronological holdout: earliest 70% for training, latest 30% for testing.
    split_idx = int(len(df) * 0.70)
    if split_idx < 20 or len(df) - split_idx < 10:
        raise ValueError("Not enough rows for the configured chronological split.")
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    test_meta = df.iloc[split_idx:][[TIME_COL, "direction"]].copy() if "direction" in df.columns else df.iloc[split_idx:][[TIME_COL]].copy()

    if y_train.nunique() < 2:
        raise ValueError(
            "Training period contains only one class. A classifier cannot learn both "
            "outcomes from this split; inspect label distribution and time split."
        )

    rf = Pipeline([
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
    majority = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", DummyClassifier(strategy="most_frequent")),
    ])

    rf.fit(X_train, y_train)
    majority.fit(X_train, y_train)
    pred = rf.predict(X_test)
    base_pred = majority.predict(X_test)
    proba = rf.predict_proba(X_test)
    classes = list(rf.named_steps["model"].classes_)
    positive_index = classes.index(1) if 1 in classes else None
    prob_win = proba[:, positive_index] if positive_index is not None else np.full(len(y_test), np.nan)

    def metrics(y_true, y_pred, p=None):
        result = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
            "precision_win": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
            "recall_win": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
            "f1_win": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
            "confusion_matrix_labels_0_1": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        }
        if p is not None and len(np.unique(y_true)) == 2:
            result["roc_auc"] = float(roc_auc_score(y_true, p))
        else:
            result["roc_auc"] = None
        return result

    rf_metrics = metrics(y_test, pred, prob_win)
    base_metrics = metrics(y_test, base_pred)
    test_meta["actual_target_tp_first"] = y_test.to_numpy()
    test_meta["rf_predicted_target"] = pred
    test_meta["rf_estimated_win_probability_pct"] = np.round(prob_win * 100, 2)
    test_meta["majority_baseline_prediction"] = base_pred
    test_meta.to_csv(PREDICTIONS_PATH, index=False)

    report = {
        "warning": (
            "EXPLORATORY ONLY: labels come from the legacy backtest and signal timestamps "
            "were flagged by the timing audit. These are not validated predictive metrics."
        ),
        "dataset_path": str(DATA_PATH),
        "rows_used": int(len(df)),
        "feature_count": int(len(candidate_cols)),
        "features": candidate_cols,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "chronological_train_period": {
            "start": str(df.iloc[0][TIME_COL]),
            "end": str(df.iloc[split_idx - 1][TIME_COL]),
        },
        "chronological_test_period": {
            "start": str(df.iloc[split_idx][TIME_COL]),
            "end": str(df.iloc[-1][TIME_COL]),
        },
        "overall_label_counts": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "train_label_counts": {str(k): int(v) for k, v in y_train.value_counts().sort_index().items()},
        "test_label_counts": {str(k): int(v) for k, v in y_test.value_counts().sort_index().items()},
        "random_forest": rf_metrics,
        "majority_class_baseline": base_metrics,
        "model_settings": {
            "n_estimators": 400,
            "max_depth": 4,
            "min_samples_leaf": 8,
            "class_weight": "balanced",
            "random_state": 42,
        },
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "EXPLORATORY RANDOM FOREST — LEGACY LABELS",
        "=" * 48,
        report["warning"],
        "",
        f"Rows used: {len(df)}",
        f"Numeric features used: {len(candidate_cols)}",
        f"Train rows: {len(X_train)} | Test rows: {len(X_test)}",
        f"Train period: {report['chronological_train_period']['start']} to {report['chronological_train_period']['end']}",
        f"Test period: {report['chronological_test_period']['start']} to {report['chronological_test_period']['end']}",
        f"Overall labels: {report['overall_label_counts']}",
        f"Test labels: {report['test_label_counts']}",
        "",
        "Random Forest metrics:",
        json.dumps(rf_metrics, indent=2),
        "",
        "Majority baseline metrics:",
        json.dumps(base_metrics, indent=2),
        "",
        f"Test predictions saved to: {PREDICTIONS_PATH}",
        f"Metrics JSON saved to: {METRICS_PATH}",
        "",
        "Do not interpret estimated win probabilities as calibrated probabilities yet.",
        "Do not use this experiment to claim validated trading performance.",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))

if __name__ == "__main__":
    main()
