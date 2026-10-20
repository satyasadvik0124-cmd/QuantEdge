"""
Generate chronological walk-forward ML scores for the existing legacy SMC trade dataset.

This is a safer diagnostic than scoring the same rows used to fit the final saved model:
each prediction is made by a model trained only on earlier rows.

Reads:
  outputs/ml/gbpusd_m15_technical_features_legacy.csv
  outputs/ml/rf_legacy_model_features.json

Writes NEW files only:
  outputs/ml/rf_walk_forward_predictions.csv
  outputs/ml/rf_walk_forward_report.txt

Does not modify strategy, original backtest results, or the saved model.

IMPORTANT: The legacy target/timestamps have known alignment limitations. Treat this as
an exploratory chronological evaluation, not proof of a tradable edge.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "outputs" / "ml" / "gbpusd_m15_technical_features_legacy.csv"
SCHEMA_PATH = ROOT / "outputs" / "ml" / "rf_legacy_model_features.json"
OUT_DIR = ROOT / "outputs" / "ml"
PREDICTIONS_PATH = OUT_DIR / "rf_walk_forward_predictions.csv"
REPORT_PATH = OUT_DIR / "rf_walk_forward_report.txt"

TARGET = "target_tp_first"
TIME_COL = "signal_time"
INITIAL_TRAIN_FRACTION = 0.70


def make_model():
    return Pipeline([
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


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Feature schema not found: {SCHEMA_PATH}")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    features = schema.get("features", [])
    if not features:
        raise ValueError("Feature schema contains no features.")

    df = pd.read_csv(DATA_PATH)
    required = {TIME_COL, TARGET, *features}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    df = df.dropna(subset=[TIME_COL, TARGET]).copy()
    df = df[df[TARGET].isin([0, 1])].sort_values(TIME_COL).reset_index(drop=True)

    X = df[features].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    y = df[TARGET].astype(int)

    initial_train_size = int(len(df) * INITIAL_TRAIN_FRACTION)
    if initial_train_size < 20 or initial_train_size >= len(df):
        raise ValueError(f"Invalid initial training size: {initial_train_size} of {len(df)} rows.")

    predictions = []
    # Predict each later row using only rows strictly earlier in time.
    # Refit each step to make the time ordering explicit and avoid future-label leakage.
    for test_idx in range(initial_train_size, len(df)):
        X_train, y_train = X.iloc[:test_idx], y.iloc[:test_idx]
        if y_train.nunique() < 2:
            continue

        model = make_model()
        model.fit(X_train, y_train)

        row_x = X.iloc[[test_idx]]
        probas = model.predict_proba(row_x)[0]
        classes = list(model.named_steps["model"].classes_)
        win_idx = classes.index(1)
        win_score = float(probas[win_idx])
        predicted_class = int(model.predict(row_x)[0])

        record = {
            "source_row_index": int(test_idx),
            "signal_time": df.iloc[test_idx][TIME_COL],
            "actual_target_tp_first": int(y.iloc[test_idx]),
            "ml_estimated_win_score": win_score,
            "ml_estimated_win_score_pct": win_score * 100.0,
            "ml_predicted_class": predicted_class,
            "training_rows_before_prediction": int(test_idx),
            "training_start": df.iloc[0][TIME_COL],
            "training_end": df.iloc[test_idx - 1][TIME_COL],
            "score_warning": "Exploratory only; legacy labels/timestamps have known limitations.",
        }
        if "result" in df.columns:
            record["legacy_result"] = df.iloc[test_idx]["result"]
        if "direction" in df.columns:
            record["direction"] = df.iloc[test_idx]["direction"]
        if "entry" in df.columns:
            record["entry"] = df.iloc[test_idx]["entry"]
        if "sl" in df.columns:
            record["sl"] = df.iloc[test_idx]["sl"]
        if "tp" in df.columns:
            record["tp"] = df.iloc[test_idx]["tp"]
        predictions.append(record)

    out = pd.DataFrame(predictions)
    if out.empty:
        raise RuntimeError("No walk-forward predictions were generated.")

    y_true = out["actual_target_tp_first"].astype(int)
    y_pred = out["ml_predicted_class"].astype(int)
    y_score = out["ml_estimated_win_score"].astype(float)

    metrics = {
        "rows_in_dataset": int(len(df)),
        "initial_training_rows": int(initial_train_size),
        "walk_forward_predictions": int(len(out)),
        "prediction_start": str(out["signal_time"].min()),
        "prediction_end": str(out["signal_time"].max()),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision_win": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_win": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_win": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, y_score)),
        "roc_auc": float(roc_auc_score(y_true, y_score)) if y_true.nunique() == 2 else None,
        "confusion_matrix_labels_0_1": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "warning": "Exploratory only. The legacy target/timestamps have known alignment limitations.",
    }

    # Write fresh files only; no strategy/backtest files are touched.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(PREDICTIONS_PATH, index=False)

    score_bins = pd.cut(
        out["ml_estimated_win_score"],
        bins=[0.0, 0.4, 0.5, 0.6, 0.7, 1.000001],
        labels=["0-<40%", "40-<50%", "50-<60%", "60-<70%", "70-100%"],
        include_lowest=True,
        right=False,
    )
    bins = out.assign(score_band=score_bins).groupby("score_band", observed=False).agg(
        trades=("actual_target_tp_first", "size"),
        wins=("actual_target_tp_first", "sum"),
        mean_score=("ml_estimated_win_score", "mean"),
        observed_win_rate=("actual_target_tp_first", "mean"),
    ).reset_index()

    lines = [
        "RANDOM FOREST WALK-FORWARD EVALUATION — EXPLORATORY",
        "=" * 58,
        "Each prediction is made using only earlier rows/labels.",
        metrics["warning"],
        "",
        f"Dataset rows: {metrics['rows_in_dataset']}",
        f"Initial training rows: {metrics['initial_training_rows']}",
        f"Walk-forward predictions: {metrics['walk_forward_predictions']}",
        f"Prediction period: {metrics['prediction_start']} to {metrics['prediction_end']}",
        "",
        "Metrics:",
        json.dumps(metrics, indent=2),
        "",
        "Confidence bands (diagnostic only):",
        bins.to_string(index=False),
        "",
        f"Predictions CSV: {PREDICTIONS_PATH}",
        f"Report: {REPORT_PATH}",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
