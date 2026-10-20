"""
QuantEdge: chronological stability check for existing walk-forward predictions.

Run from the project root:
    python .\analysis\analyze_walk_forward_stability.py

Reads:
    outputs/ml/walk_forward_evaluation/gbpusd_walk_forward_predictions.csv
    outputs/ml/walk_forward_evaluation/xauusd_walk_forward_predictions.csv

Writes NEW reports under:
    outputs/ml/walk_forward_evaluation/stability/

This script does not retrain models, change strategy rules, or modify existing outputs.
It splits each pair's already-scored predictions into three chronological sections and
compares all scored trades against the >=60% score group in each section.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "outputs" / "ml" / "walk_forward_evaluation"
OUT_DIR = IN_DIR / "stability"
PAIRS = ["GBPUSD", "XAUUSD"]


def metrics(group, pair, period, selection):
    resolved = group[group["entry_touch_result"].isin(["WIN", "LOSS"])].sort_values(
        ["signal_time", "signal_row_id"]
    )
    r = pd.to_numeric(resolved["entry_touch_R"], errors="coerce").dropna()
    wins = int(resolved["entry_touch_result"].eq("WIN").sum())
    losses = int(resolved["entry_touch_result"].eq("LOSS").sum())
    gross_profit = float(r[r > 0].sum())
    gross_loss = float(-r[r < 0].sum())
    pf = gross_profit / gross_loss if gross_loss else (np.inf if gross_profit else np.nan)
    equity = r.cumsum()
    dd = float((equity.cummax() - equity).max()) if len(equity) else 0.0
    return {
        "pair": pair,
        "chronological_period": period,
        "selection": selection,
        "scored_signals": int(group["ml_estimated_win_score"].notna().sum()),
        "resolved_trades": len(resolved),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(100 * wins / len(resolved), 2) if len(resolved) else np.nan,
        "net_R": round(float(r.sum()), 2),
        "profit_factor": round(pf, 4) if np.isfinite(pf) else ("Infinity" if pf == np.inf else np.nan),
        "max_drawdown_R_signal_order": round(dd, 2),
        "mean_score_pct": round(float(group["ml_estimated_win_score"].mean() * 100), 2)
            if group["ml_estimated_win_score"].notna().any() else np.nan,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for pair in PAIRS:
        path = IN_DIR / f"{pair.lower()}_walk_forward_predictions.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run the walk-forward evaluation first.")
        df = pd.read_csv(path)
        required = [
            "signal_time", "signal_row_id", "ml_estimated_win_score",
            "entry_touch_result", "entry_touch_R",
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"{path.name} missing columns: {missing}")
        df["signal_time"] = pd.to_datetime(df["signal_time"], errors="coerce")
        df["ml_estimated_win_score"] = pd.to_numeric(df["ml_estimated_win_score"], errors="coerce")
        df["entry_touch_R"] = pd.to_numeric(df["entry_touch_R"], errors="coerce")
        df["entry_touch_result"] = df["entry_touch_result"].astype(str).str.upper().str.strip()
        df = df[df["ml_estimated_win_score"].notna() & df["signal_time"].notna()].sort_values(
            ["signal_time", "signal_row_id"]
        ).reset_index(drop=True)

        if df.empty:
            print(f"[{pair}] No scored predictions found.")
            continue

        # Equal-count chronological thirds; boundaries are derived only from timestamps,
        # not from outcomes or model performance.
        split_indices = np.array_split(np.arange(len(df)), 3)
        for j, indices in enumerate(split_indices, start=1):
            if len(indices) == 0:
                continue
            part = df.iloc[indices].copy()
            start = part["signal_time"].min().strftime("%Y-%m-%d")
            end = part["signal_time"].max().strftime("%Y-%m-%d")
            period = f"Third {j} ({start} to {end})"
            all_rows.append(metrics(part, pair, period, "ALL SCORED"))
            high = part[part["ml_estimated_win_score"] >= 0.60]
            all_rows.append(metrics(high, pair, period, "Score >=60%"))

        # Full-period reference.
        all_rows.append(metrics(df, pair, "FULL SCORED PERIOD", "ALL SCORED"))
        all_rows.append(metrics(df[df["ml_estimated_win_score"] >= 0.60], pair,
                                "FULL SCORED PERIOD", "Score >=60%"))

    result = pd.DataFrame(all_rows)
    out_csv = OUT_DIR / "chronological_stability_summary.csv"
    out_txt = OUT_DIR / "chronological_stability_report.txt"
    result.to_csv(out_csv, index=False)
    notes = [
        "QUANTEDGE — CHRONOLOGICAL WALK-FORWARD STABILITY CHECK",
        "=" * 68,
        "The scored prediction rows are split into three equal-count chronological sections per pair.",
        "This is a descriptive stability check, not an independent new test set.",
        "Scores are raw Random Forest scores, not calibrated probabilities.",
        "Drawdown is calculated in signal order and is not a portfolio simulation.",
        "The outcomes retain the existing Entry-Touch backtest assumptions and exclude trading costs.",
        "Inspect high-score sample sizes before interpreting changes in win rate or profit factor.",
        "",
        result.to_string(index=False),
    ]
    out_txt.write_text("\n".join(notes), encoding="utf-8")
    print(result.to_string(index=False))
    print(f"\nSaved CSV: {out_csv}")
    print(f"Saved report: {out_txt}")


if __name__ == "__main__":
    main()
