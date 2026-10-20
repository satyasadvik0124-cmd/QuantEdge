"""
Summarize how walk-forward ML scores relate to legacy target labels at different
experimental thresholds. This is diagnostic only, not a strategy backtest.

Reads:
  outputs/ml/rf_walk_forward_predictions.csv

Writes new files:
  outputs/ml/rf_walk_forward_threshold_analysis.csv
  outputs/ml/rf_walk_forward_threshold_analysis.txt

No strategy/backtest/model files are modified.
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "ml" / "rf_walk_forward_predictions.csv"
OUT_CSV = ROOT / "outputs" / "ml" / "rf_walk_forward_threshold_analysis.csv"
OUT_TXT = ROOT / "outputs" / "ml" / "rf_walk_forward_threshold_analysis.txt"

THRESHOLDS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]


def summarize(name, subset, total):
    n = len(subset)
    wins = int(subset["actual_target_tp_first"].sum()) if n else 0
    return {
        "group": name,
        "trades": n,
        "coverage_pct": (n / total * 100) if total else np.nan,
        "legacy_label_wins": wins,
        "legacy_label_win_rate_pct": (wins / n * 100) if n else np.nan,
        "mean_score_pct": (
            subset["ml_estimated_win_score"].mean() * 100 if n else np.nan
        ),
    }


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Walk-forward prediction file not found: {INPUT}")

    df = pd.read_csv(INPUT)
    needed = {"actual_target_tp_first", "ml_estimated_win_score"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Input is missing columns: {sorted(missing)}")

    df["actual_target_tp_first"] = pd.to_numeric(
        df["actual_target_tp_first"], errors="coerce"
    )
    df["ml_estimated_win_score"] = pd.to_numeric(
        df["ml_estimated_win_score"], errors="coerce"
    )
    df = df.dropna(subset=["actual_target_tp_first", "ml_estimated_win_score"])
    df = df[df["actual_target_tp_first"].isin([0, 1])].copy()
    df["actual_target_tp_first"] = df["actual_target_tp_first"].astype(int)
    total = len(df)
    baseline = summarize("All walk-forward predictions (baseline)", df, total)

    rows = [baseline]
    for threshold in THRESHOLDS:
        subset = df[df["ml_estimated_win_score"] >= threshold]
        rows.append(summarize(f"Score >= {threshold:.0%}", subset, total))

    # Include score bands for an easy visual diagnostic.
    bins = [0.0, 0.4, 0.5, 0.6, 0.7, 1.000001]
    labels = ["0-<40%", "40-<50%", "50-<60%", "60-<70%", "70-100%"]
    df["score_band"] = pd.cut(
        df["ml_estimated_win_score"], bins=bins, labels=labels,
        include_lowest=True, right=False
    )
    band_table = df.groupby("score_band", observed=False).agg(
        trades=("actual_target_tp_first", "size"),
        legacy_label_wins=("actual_target_tp_first", "sum"),
        mean_score=("ml_estimated_win_score", "mean"),
        observed_label_win_rate=("actual_target_tp_first", "mean"),
    ).reset_index()
    band_table["mean_score_pct"] = band_table["mean_score"] * 100
    band_table["observed_label_win_rate_pct"] = band_table["observed_label_win_rate"] * 100
    band_table.drop(columns=["mean_score", "observed_label_win_rate"], inplace=True)

    result = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)

    lines = [
        "WALK-FORWARD SCORE THRESHOLD DIAGNOSTIC",
        "=" * 48,
        "These are associations with legacy labels, NOT strategy backtest results.",
        "The legacy labels/timestamps have known alignment limitations.",
        "Do not select a threshold based only on this small sample.",
        "",
        f"Walk-forward records: {total}",
        f"Overall legacy-label win rate: {baseline['legacy_label_win_rate_pct']:.2f}%",
        "",
        "Threshold summary:",
        result.to_string(index=False, float_format=lambda x: f"{x:.2f}"),
        "",
        "Score bands:",
        band_table.to_string(index=False, float_format=lambda x: f"{x:.2f}"),
        "",
        f"CSV: {OUT_CSV}",
        f"Report: {OUT_TXT}",
    ]
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
