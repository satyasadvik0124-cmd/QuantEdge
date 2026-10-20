"""
Compare several ML confidence models for existing XAUUSD M15 SMC trades.

Reads only the already-created:
  outputs/ml/xauusd_m15_technical_features.csv

Writes NEW diagnostics only:
  outputs/ml/xauusd_model_comparison_walkforward.csv
  outputs/ml/xauusd_model_comparison_summary.csv
  outputs/ml/xauusd_model_comparison_score_bands.csv
  outputs/ml/xauusd_model_comparison_report.txt

Does not modify signals, entries, SL, TP, RR, original backtest results, or any saved model.
Refuses to overwrite outputs unless --overwrite is explicitly supplied.

Evaluation:
- chronological expanding walk-forward predictions
- each prediction uses only earlier rows for model fitting
- compares a naive baseline, Logistic Regression, Random Forest, Extra Trees,
  and Gradient Boosting
- reports ranking and probability-quality metrics; it does not automatically filter trades
  or claim scores are calibrated probabilities.

Important limitation:
Existing labels come from the legacy backtest. Exit timestamps are not available here,
so overlapping/open trade label timing cannot be purged exactly. Treat findings as exploratory.
"""

from pathlib import Path
import argparse
import json
import warnings

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
ML_DIR = ROOT / "outputs" / "ml"
DATA_FILE = ML_DIR / "xauusd_m15_technical_features.csv"
SCHEMA_FILE = ML_DIR / "xauusd_rf_model_features.json"

PREDICTIONS_FILE = ML_DIR / "xauusd_model_comparison_walkforward.csv"
SUMMARY_FILE = ML_DIR / "xauusd_model_comparison_summary.csv"
BANDS_FILE = ML_DIR / "xauusd_model_comparison_score_bands.csv"
REPORT_FILE = ML_DIR / "xauusd_model_comparison_report.txt"

TARGET = "target_tp_first"
TIME_COL = "signal_time"
INITIAL_TRAIN_FRACTION = 0.70
MIN_INITIAL_TRAIN = 100
RANDOM_STATE = 42


def model_templates():
    return {
        "Prior baseline": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DummyClassifier(strategy="prior")),
        ]),
        "Logistic Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(
                C=0.1, class_weight="balanced", max_iter=3000,
                random_state=RANDOM_STATE
            )),
        ]),
        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=300, max_depth=4, min_samples_leaf=8,
                max_features="sqrt", class_weight="balanced",
                random_state=RANDOM_STATE, n_jobs=-1
            )),
        ]),
        "Extra Trees": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesClassifier(
                n_estimators=300, max_depth=4, min_samples_leaf=8,
                max_features="sqrt", class_weight="balanced",
                random_state=RANDOM_STATE, n_jobs=-1
            )),
        ]),
        "Gradient Boosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingClassifier(
                n_estimators=80, learning_rate=0.03, max_depth=1,
                min_samples_leaf=10, random_state=RANDOM_STATE
            )),
        ]),
    }


def score_positive_class(model, row):
    fitted_model = model.named_steps["model"]
    probabilities = model.predict_proba(row)[0]
    classes = list(fitted_model.classes_)
    if 1 not in classes:
        return 0.0
    return float(probabilities[classes.index(1)])


def safe_auc(y_true, scores):
    try:
        return float(roc_auc_score(y_true, scores))
    except ValueError:
        return float("nan")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Replace only this script's four comparison output files."
    )
    args = parser.parse_args()

    required_files = [DATA_FILE, SCHEMA_FILE]
    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(
                f"Required file not found: {path}\n"
                "Run train_xauusd_rf_model.py first so the feature dataset and schema exist."
            )

    outputs = [PREDICTIONS_FILE, SUMMARY_FILE, BANDS_FILE, REPORT_FILE]
    existing = [p for p in outputs if p.exists()]
    if existing and not args.overwrite:
        raise FileExistsError(
            "To prevent overwriting, this comparison stopped because these outputs already exist:\n"
            + "\n".join(str(p) for p in existing)
            + "\nUse --overwrite only if you intentionally want to replace these comparison reports."
        )

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    features = schema.get("features", [])
    if not features:
        raise ValueError("No feature list found in the XAUUSD model schema.")

    df = pd.read_csv(DATA_FILE)
    required_cols = {TIME_COL, TARGET, *features}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Feature dataset missing columns: {sorted(missing)}")

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    if "feature_status" in df.columns:
        df = df[df["feature_status"].astype(str).eq("OK")].copy()

    df = df.dropna(subset=[TIME_COL, TARGET]).copy()
    df = df[df[TARGET].isin([0, 1])].sort_values(TIME_COL).reset_index(drop=True)
    if len(df) < MIN_INITIAL_TRAIN + 30:
        raise ValueError(
            f"Only {len(df)} eligible rows. Need at least {MIN_INITIAL_TRAIN + 30} "
            "for a meaningful chronological comparison."
        )

    X = df[features].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    y = df[TARGET].astype(int)

    start_idx = max(MIN_INITIAL_TRAIN, int(len(df) * INITIAL_TRAIN_FRACTION))
    if start_idx >= len(df) - 1:
        raise ValueError("Not enough rows remain for walk-forward testing.")

    templates = model_templates()
    records = []
    warnings.filterwarnings("ignore", category=UserWarning)

    print(f"Eligible rows: {len(df)}")
    print(f"Initial training rows: {start_idx}")
    print(f"Walk-forward test rows per model: {len(df) - start_idx}")
    print("Running expanding chronological evaluation; this may take a few minutes...")

    for model_name, template in templates.items():
        for test_idx in range(start_idx, len(df)):
            X_train = X.iloc[:test_idx]
            y_train = y.iloc[:test_idx]
            if y_train.nunique() < 2:
                continue

            model = clone(template)
            model.fit(X_train, y_train)
            row_x = X.iloc[[test_idx]]
            score = score_positive_class(model, row_x)
            predicted = int(score >= 0.5)

            record = {
                "model": model_name,
                "source_row_index": test_idx,
                "signal_time": df.iloc[test_idx][TIME_COL],
                "direction": df.iloc[test_idx].get("direction", ""),
                "result": df.iloc[test_idx].get("result", ""),
                "actual_label": int(y.iloc[test_idx]),
                "predicted_class_at_50pct": predicted,
                "ml_confidence_score": score,
                "ml_confidence_score_pct": round(score * 100, 2),
                "training_rows": test_idx,
                "training_end_time": df.iloc[test_idx - 1][TIME_COL],
            }
            for col in ("entry", "sl", "tp", "feature_candle_time"):
                if col in df.columns:
                    record[col] = df.iloc[test_idx][col]
            records.append(record)

        print(f"Completed: {model_name}")

    predictions = pd.DataFrame(records)
    if predictions.empty:
        raise RuntimeError("No walk-forward predictions generated.")

    summary_rows = []
    band_rows = []
    for model_name, group in predictions.groupby("model", sort=False):
        actual = group["actual_label"].astype(int).to_numpy()
        scores = group["ml_confidence_score"].astype(float).to_numpy()
        pred = group["predicted_class_at_50pct"].astype(int).to_numpy()

        summary_rows.append({
            "model": model_name,
            "test_trades": len(group),
            "actual_wins": int(actual.sum()),
            "observed_win_rate_pct": round(100 * float(actual.mean()), 2),
            "accuracy_pct": round(100 * accuracy_score(actual, pred), 2),
            "balanced_accuracy_pct": round(100 * balanced_accuracy_score(actual, pred), 2),
            "precision_win_pct": round(100 * precision_score(actual, pred, zero_division=0), 2),
            "recall_win_pct": round(100 * recall_score(actual, pred, zero_division=0), 2),
            "f1_win_pct": round(100 * f1_score(actual, pred, zero_division=0), 2),
            "roc_auc": round(safe_auc(actual, scores), 4),
            "average_precision": round(float(average_precision_score(actual, scores)), 4),
            "brier_score_lower_is_better": round(float(brier_score_loss(actual, scores)), 4),
            "log_loss_lower_is_better": round(float(log_loss(actual, np.clip(scores, 1e-6, 1-1e-6), labels=[0, 1])), 4),
        })

        bins = [-np.inf, 0.40, 0.50, 0.60, 0.70, np.inf]
        labels = ["Below 40%", "40–49.99%", "50–59.99%", "60–69.99%", "70%+"]
        band = pd.cut(group["ml_confidence_score"], bins=bins, labels=labels, right=False)
        temp = group.assign(confidence_band=band)
        for band_name, band_group in temp.groupby("confidence_band", observed=False):
            count = len(band_group)
            wins = int(band_group["actual_label"].sum()) if count else 0
            band_rows.append({
                "model": model_name,
                "confidence_band": str(band_name),
                "trades": count,
                "wins": wins,
                "losses": count - wins,
                "observed_win_rate_pct": round(100 * wins / count, 2) if count else np.nan,
                "mean_model_score_pct": round(100 * band_group["ml_confidence_score"].mean(), 2) if count else np.nan,
            })

    summary = pd.DataFrame(summary_rows)
    # Rank only as a diagnostic; avoid declaring a winner from one metric alone.
    summary["rank_brier"] = summary["brier_score_lower_is_better"].rank(method="min", ascending=True)
    summary["rank_auc"] = summary["roc_auc"].rank(method="min", ascending=False)
    summary["rank_average_precision"] = summary["average_precision"].rank(method="min", ascending=False)
    summary["mean_diagnostic_rank"] = summary[
        ["rank_brier", "rank_auc", "rank_average_precision"]
    ].mean(axis=1).round(2)
    summary = summary.sort_values(
        ["mean_diagnostic_rank", "brier_score_lower_is_better"],
        ascending=[True, True]
    ).reset_index(drop=True)

    bands = pd.DataFrame(band_rows)
    predictions.to_csv(PREDICTIONS_FILE, index=False)
    summary.to_csv(SUMMARY_FILE, index=False)
    bands.to_csv(BANDS_FILE, index=False)

    report_lines = [
        "XAUUSD M15 — MODEL COMPARISON WITH CHRONOLOGICAL WALK-FORWARD PREDICTIONS",
        "=" * 78,
        f"Eligible dataset rows: {len(df)}",
        f"Initial train rows: {start_idx}",
        f"Walk-forward test rows per model: {len(df) - start_idx}",
        f"Test period: {df.iloc[start_idx][TIME_COL]} to {df.iloc[-1][TIME_COL]}",
        "",
        "MODEL SUMMARY (diagnostic ranking only; not a trading recommendation)",
        summary.to_string(index=False),
        "",
        "CONFIDENCE BAND WIN RATES",
        bands.to_string(index=False),
        "",
        "Interpretation guidance:",
        "- Prefer consistent ranking (higher ROC-AUC / average precision) and lower Brier/log loss.",
        "- Compare against the Prior baseline; a complex model that does not beat it is not useful.",
        "- A score band is only informative when it has enough trades and repeats across periods.",
        "- Do not choose a confidence threshold from this report alone.",
        "",
        "Important limitations:",
        "- Results/outcomes come from the existing legacy backtest and have not been independently validated.",
        "- Exit times are not present, so overlapping trade labels cannot be purged exactly.",
        "- Signal timestamps/features inherit the existing recorded-timestamp convention.",
        "- Scores are not calibrated win probabilities and this script does not filter or alter trades.",
        "",
        "Created files:",
        str(PREDICTIONS_FILE),
        str(SUMMARY_FILE),
        str(BANDS_FILE),
        str(REPORT_FILE),
    ]
    REPORT_FILE.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("\n===== WALK-FORWARD MODEL COMPARISON COMPLETE =====")
    print(summary.to_string(index=False))
    print("\nCreated new files:")
    for path in outputs:
        print(path)
    print("\nNo SMC strategy, signal, entry, SL, TP, RR, backtest, or saved model was changed.")


if __name__ == "__main__":
    main()
