"""
Analyze Random Forest confidence scores from the legacy test predictions.

Reads:
  outputs/ml/rf_legacy_test_predictions.csv

Writes:
  outputs/ml/rf_legacy_confidence_bins.csv
  outputs/ml/rf_legacy_confidence_report.txt

This script does not retrain the model and does not modify SMC/backtest files.
WARNING: These scores are exploratory because legacy labels/timestamps have
known timing-alignment limitations. Probability calibration is not guaranteed.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "outputs" / "ml" / "rf_legacy_test_predictions.csv"
OUTDIR = ROOT / "outputs" / "ml"
BINS_PATH = OUTDIR / "rf_legacy_confidence_bins.csv"
REPORT_PATH = OUTDIR / "rf_legacy_confidence_report.txt"

TARGET_COL = "actual_target_tp_first"
PROB_COL = "rf_estimated_win_probability_pct"

def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {IN_PATH}. Run train_rf_legacy_experiment.py first."
        )
    df = pd.read_csv(IN_PATH)
    missing = [c for c in [TARGET_COL, PROB_COL] if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns {missing}. Found columns: {df.columns.tolist()}"
        )

    df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce")
    df[PROB_COL] = pd.to_numeric(df[PROB_COL], errors="coerce")
    df = df.dropna(subset=[TARGET_COL, PROB_COL]).copy()
    df = df[df[TARGET_COL].isin([0, 1])]
    df["estimated_win_probability"] = df[PROB_COL] / 100.0
    df["predicted_class_at_50pct"] = (df["estimated_win_probability"] >= 0.5).astype(int)

    # Explicit, interpretable bins; final bin includes 100%.
    edges = [0.0, 0.4, 0.5, 0.6, 0.7, 1.0000001]
    labels = ["0–<40%", "40–<50%", "50–<60%", "60–<70%", "70–100%"]
    df["confidence_band"] = pd.cut(
        df["estimated_win_probability"],
        bins=edges,
        labels=labels,
        right=False,
        include_lowest=True,
    )

    grouped = df.groupby("confidence_band", observed=False).agg(
        trade_count=(TARGET_COL, "size"),
        observed_wins=(TARGET_COL, "sum"),
        mean_estimated_win_probability=("estimated_win_probability", "mean"),
        observed_win_rate=(TARGET_COL, "mean"),
    ).reset_index()
    grouped["mean_estimated_win_probability_pct"] = grouped["mean_estimated_win_probability"] * 100
    grouped["observed_win_rate_pct"] = grouped["observed_win_rate"] * 100
    grouped = grouped[
        ["confidence_band", "trade_count", "observed_wins",
         "mean_estimated_win_probability_pct", "observed_win_rate_pct"]
    ]
    grouped.to_csv(BINS_PATH, index=False)

    y = df[TARGET_COL].astype(int)
    p = df["estimated_win_probability"].clip(0, 1)
    brier = float(brier_score_loss(y, p))
    auc = float(roc_auc_score(y, p)) if y.nunique() == 2 else None
    actual_win_rate = float(y.mean() * 100)
    mean_score = float(p.mean() * 100)
    pred_positive = int((df["predicted_class_at_50pct"] == 1).sum())
    correct_at_50 = float((df["predicted_class_at_50pct"] == y).mean() * 100)

    lines = [
        "EXPLORATORY RANDOM FOREST — CONFIDENCE SCORE REVIEW",
        "=" * 58,
        "WARNING: Legacy signal timestamps/labels have known alignment limitations.",
        "These estimates are not validated probabilities or evidence of profitability.",
        "",
        f"Test trades analyzed: {len(df)}",
        f"Observed legacy-label win rate: {actual_win_rate:.2f}%",
        f"Mean estimated win probability: {mean_score:.2f}%",
        f"Brier score (lower is better; 0 is perfect): {brier:.4f}",
        f"ROC-AUC from saved probabilities: {auc:.4f}" if auc is not None else "ROC-AUC: not available (one class only)",
        f"Trades scored >=50%: {pred_positive}",
        f"Accuracy using a 50% probability threshold: {correct_at_50:.2f}%",
        "",
        "Confidence-band results:",
        grouped.to_string(index=False, formatters={
            "mean_estimated_win_probability_pct": lambda x: f"{x:.2f}",
            "observed_win_rate_pct": lambda x: f"{x:.2f}",
        }),
        "",
        "Interpretation guidance:",
        "- Compare observed win rate with mean estimated probability in each band.",
        "- Small bands are noisy; do not draw conclusions from a few trades.",
        "- Empty bands are not evidence of success or failure.",
        "- A high score is not yet a calibrated real-world win probability.",
        "",
        f"Band table saved to: {BINS_PATH}",
    ]
    REPORT_PATH.write_text("\\n".join(lines), encoding="utf-8")
    print("\\n".join(lines))

if __name__ == "__main__":
    main()
