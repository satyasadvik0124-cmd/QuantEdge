"""
Build and evaluate a separate XAUUSD M15 Random Forest confidence model.

Safety:
- Reads existing XAUUSD candles, SMC signals, and V1 backtest outcomes.
- Verifies signal/outcome rows match before training.
- Uses only fully completed candles at or before each recorded signal timestamp.
- Uses a chronological train/test split.
- Does NOT modify SMC rules, signals, entries, SL, TP, RR, the original backtest,
  or any existing GBPUSD model.
- Refuses to overwrite this script's XAUUSD output artifacts unless --overwrite
  is explicitly supplied.

Important: the legacy backtest outcomes themselves may have timing/entry
assumptions that have not been independently validated. Model scores are
experimental and not calibrated win probabilities.
"""

from pathlib import Path
import argparse
import json
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
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

# Import the exact indicator formulas from the existing feature builder.
ANALYSIS_DIR = Path(__file__).resolve().parent
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from prepare_technical_dataset import build_features, find_column

BASE_DIR = ANALYSIS_DIR.parent
DATA_FILE = BASE_DIR / "data" / "XAUUSD_M15_5Y.csv"
SIGNALS_FILE = BASE_DIR / "outputs" / "signals_v3.csv"
RESULTS_FILE = BASE_DIR / "outputs" / "backtest_results_v1.csv"
OUTPUT_DIR = BASE_DIR / "outputs" / "ml"

MODEL_FILE = OUTPUT_DIR / "xauusd_rf_model.joblib"
SCHEMA_FILE = OUTPUT_DIR / "xauusd_rf_model_features.json"
REPORT_FILE = OUTPUT_DIR / "xauusd_rf_training_report.txt"
TEST_PREDICTIONS_FILE = OUTPUT_DIR / "xauusd_rf_test_predictions.csv"
FEATURE_DATA_FILE = OUTPUT_DIR / "xauusd_m15_technical_features.csv"

BAR_MINUTES = 15
MIN_HISTORY = 60
TEST_FRACTION = 0.20

FEATURE_COLS = [
    "rsi_14",
    "macd_atr",
    "macd_hist_atr",
    "ema9_vs_ema21_atr",
    "ema21_vs_ema50_atr",
    "close_vs_ema9_atr",
    "atr_14",
    "adx_14",
    "bb_position",
    "return_1",
    "return_4",
    "return_16",
    "candle_body_ratio",
    "candle_direction",
    "direction_buy",
    "risk_distance",
    "risk_distance_atr",
]


def read_candles():
    raw = pd.read_csv(DATA_FILE)
    time_col = find_column(raw, ["time", "datetime", "date", "timestamp"], "timestamp")
    open_col = find_column(raw, ["open", "o"], "open")
    high_col = find_column(raw, ["high", "h"], "high")
    low_col = find_column(raw, ["low", "l"], "low")
    close_col = find_column(raw, ["close", "c"], "close")

    candles = pd.DataFrame({
        "time": pd.to_datetime(raw[time_col], errors="coerce"),
        "open": pd.to_numeric(raw[open_col], errors="coerce"),
        "high": pd.to_numeric(raw[high_col], errors="coerce"),
        "low": pd.to_numeric(raw[low_col], errors="coerce"),
        "close": pd.to_numeric(raw[close_col], errors="coerce"),
    })
    candles = (
        candles.dropna()
        .sort_values("time")
        .drop_duplicates("time", keep="last")
        .reset_index(drop=True)
    )
    return build_features(candles)


def read_and_verify_trades():
    signals = pd.read_csv(SIGNALS_FILE)
    results = pd.read_csv(RESULTS_FILE)

    required_signals = {"signal_time", "direction", "entry", "sl", "tp"}
    required_results = {"signal_time", "direction", "entry", "sl", "tp", "result"}
    if not required_signals.issubset(signals.columns):
        raise ValueError(f"Signals file missing columns: {sorted(required_signals - set(signals.columns))}")
    if not required_results.issubset(results.columns):
        raise ValueError(f"Results file missing columns: {sorted(required_results - set(results.columns))}")

    for df in (signals, results):
        df["signal_time"] = pd.to_datetime(df["signal_time"], errors="coerce")
        df["direction"] = df["direction"].astype(str).str.upper().str.strip()
        for col in ("entry", "sl", "tp"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if len(signals) != len(results):
        raise ValueError(
            f"Row count mismatch: signals={len(signals)}, results={len(results)}. "
            "Training stopped to avoid mismatched labels."
        )

    # Validate every row, not only the first row. This assumes the existing
    # backtest result file preserves signal order, as the current files do.
    for col in ("signal_time", "direction"):
        if not signals[col].equals(results[col]):
            raise ValueError(
                f"Signal/result mismatch in '{col}'. Training stopped; inspect files before proceeding."
            )
    for col in ("entry", "sl", "tp"):
        if not np.allclose(
            signals[col].to_numpy(dtype=float),
            results[col].to_numpy(dtype=float),
            rtol=0,
            atol=1e-7,
            equal_nan=True,
        ):
            raise ValueError(
                f"Signal/result mismatch in '{col}'. Training stopped; inspect files before proceeding."
            )

    results["result"] = results["result"].astype(str).str.upper().str.strip()
    return results


def build_dataset(candles, trades):
    rows = []
    for trade_id, trade in trades.reset_index(drop=True).iterrows():
        t = trade["signal_time"]
        out = {
            "trade_id": trade_id,
            "signal_time": t,
            "direction": trade["direction"],
            "entry": trade["entry"],
            "sl": trade["sl"],
            "tp": trade["tp"],
            "result": trade["result"],
            "feature_candle_time": pd.NaT,
            "feature_status": "",
        }

        if pd.isna(t):
            out["feature_status"] = "INVALID_SIGNAL_TIME"
            rows.append(out)
            continue

        eligible = candles[candles["time"] + pd.Timedelta(minutes=BAR_MINUTES) <= t]
        if eligible.empty:
            out["feature_status"] = "NO_COMPLETED_CANDLE_BEFORE_SIGNAL"
            rows.append(out)
            continue

        candle = eligible.iloc[-1]
        out["feature_candle_time"] = candle["time"]
        if len(eligible) < MIN_HISTORY:
            out["feature_status"] = "INSUFFICIENT_HISTORY"
            rows.append(out)
            continue

        risk = (
            trade["entry"] - trade["sl"]
            if trade["direction"] == "BUY"
            else trade["sl"] - trade["entry"]
        )
        atr = candle.get("atr_14", np.nan)

        for col in FEATURE_COLS:
            if col == "direction_buy":
                out[col] = int(trade["direction"] == "BUY")
            elif col == "risk_distance":
                out[col] = risk
            elif col == "risk_distance_atr":
                out[col] = risk / atr if pd.notna(atr) and atr != 0 else np.nan
            else:
                out[col] = candle.get(col, np.nan)

        out["feature_status"] = (
            "OK" if all(pd.notna(out.get(c, np.nan)) for c in FEATURE_COLS)
            and np.isfinite([out[c] for c in FEATURE_COLS]).all()
            else "MISSING_OR_NONFINITE_FEATURES"
        )
        rows.append(out)

    dataset = pd.DataFrame(rows)
    dataset["target_tp_first"] = dataset["result"].map({"WIN": 1, "LOSS": 0})
    dataset = dataset[dataset["result"].isin(["WIN", "LOSS"])].copy()
    return dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing the XAUUSD model/report artifacts created by this script.",
    )
    args = parser.parse_args()

    for path in (DATA_FILE, SIGNALS_FILE, RESULTS_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    output_files = [
        MODEL_FILE, SCHEMA_FILE, REPORT_FILE, TEST_PREDICTIONS_FILE, FEATURE_DATA_FILE
    ]
    existing = [str(p) for p in output_files if p.exists()]
    if existing and not args.overwrite:
        raise FileExistsError(
            "To avoid overwriting files, training stopped because these outputs already exist:\n"
            + "\n".join(existing)
            + "\nUse --overwrite only if you intentionally want to replace these XAUUSD artifacts."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candles = read_candles()
    trades = read_and_verify_trades()
    dataset = build_dataset(candles, trades)

    eligible = dataset[
        (dataset["feature_status"] == "OK")
        & dataset["target_tp_first"].notna()
    ].copy()
    eligible = eligible.sort_values("signal_time").reset_index(drop=True)

    if len(eligible) < 30:
        raise ValueError(f"Only {len(eligible)} eligible labeled trades; not enough for this split.")

    X = eligible[FEATURE_COLS].apply(pd.to_numeric, errors="coerce")
    y = eligible["target_tp_first"].astype(int)
    if X.isna().any().any() or not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("Feature matrix contains missing/non-finite values; training stopped.")
    if y.nunique() < 2:
        raise ValueError("Labels contain only one class; training stopped.")

    split_at = int(len(eligible) * (1 - TEST_FRACTION))
    if split_at <= 0 or split_at >= len(eligible):
        raise ValueError("Could not create chronological train/test split.")

    X_train, X_test = X.iloc[:split_at], X.iloc[split_at:]
    y_train, y_test = y.iloc[:split_at], y.iloc[split_at:]

    if y_train.nunique() < 2 or y_test.nunique() < 2:
        raise ValueError(
            "Chronological split does not contain both classes in train and test. "
            "Do not use a random split to hide this; inspect the label chronology."
        )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, list(model.classes_).index(1)]

    try:
        auc = roc_auc_score(y_test, proba)
    except ValueError:
        auc = float("nan")

    metrics = {
        "test_accuracy": accuracy_score(y_test, pred),
        "test_balanced_accuracy": balanced_accuracy_score(y_test, pred),
        "test_precision_win": precision_score(y_test, pred, zero_division=0),
        "test_recall_win": recall_score(y_test, pred, zero_division=0),
        "test_f1_win": f1_score(y_test, pred, zero_division=0),
        "test_roc_auc": auc,
        "test_brier_score": brier_score_loss(y_test, proba),
    }

    test_out = eligible.iloc[split_at:][
        ["trade_id", "signal_time", "direction", "entry", "sl", "tp", "result", "feature_candle_time"]
    ].copy()
    test_out["actual_label"] = y_test.to_numpy()
    test_out["predicted_class"] = pred
    test_out["ml_estimated_win_score"] = proba
    test_out["ml_estimated_win_score_pct"] = np.round(proba * 100, 2)
    test_out.to_csv(TEST_PREDICTIONS_FILE, index=False)

    dataset.to_csv(FEATURE_DATA_FILE, index=False)
    joblib.dump(model, MODEL_FILE)

    schema = {
        "instrument": "XAUUSD",
        "timeframe": "M15",
        "target": "target_tp_first",
        "time_column": "signal_time",
        "features": FEATURE_COLS,
        "feature_candle_rule": "latest candle whose open time + 15 minutes <= signal_time",
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "training_start": str(eligible.iloc[0]["signal_time"]),
        "training_end": str(eligible.iloc[split_at - 1]["signal_time"]),
        "test_start": str(eligible.iloc[split_at]["signal_time"]),
        "test_end": str(eligible.iloc[-1]["signal_time"]),
        "warning": (
            "Experimental model. Legacy backtest outcomes and recorded signal timestamps "
            "have not been independently validated; scores are not calibrated win probabilities."
        ),
    }
    with SCHEMA_FILE.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    report_lines = [
        "XAUUSD M15 RANDOM FOREST — CHRONOLOGICAL EVALUATION",
        "=" * 58,
        f"Candle rows: {len(candles)}",
        f"Signal/result rows verified: {len(trades)}",
        f"Eligible labeled rows: {len(eligible)}",
        f"Rows excluded for feature availability/quality: {len(trades) - len(eligible)}",
        f"WIN labels among eligible rows: {(y == 1).sum()}",
        f"LOSS labels among eligible rows: {(y == 0).sum()}",
        f"Train rows (earlier 80%): {len(X_train)}",
        f"Test rows (latest 20%): {len(X_test)}",
        f"Train period: {eligible.iloc[0]['signal_time']} to {eligible.iloc[split_at - 1]['signal_time']}",
        f"Test period: {eligible.iloc[split_at]['signal_time']} to {eligible.iloc[-1]['signal_time']}",
        "",
        "TEST METRICS",
        "-" * 58,
    ]
    report_lines += [f"{k}: {v:.4f}" for k, v in metrics.items()]
    report_lines += [
        "",
        "Confusion matrix [rows=actual 0/1, columns=predicted 0/1]:",
        str(confusion_matrix(y_test, pred, labels=[0, 1])),
        "",
        "WARNING: The test period is chronological, but legacy labels and signal timestamps",
        "have not been independently validated. Treat scores as experimental, not calibrated",
        "probabilities. This script does not modify strategy rules or original backtest files.",
    ]
    REPORT_FILE.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("\n===== XAUUSD RF TRAINING COMPLETE =====")
    print(f"Candles loaded: {len(candles):,}")
    print(f"Signals/results verified: {len(trades):,}")
    print(f"Eligible labeled trades: {len(eligible):,}")
    print(f"Train rows: {len(X_train):,} | Test rows: {len(X_test):,}")
    print("\nChronological test metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value:.4f}")
    print("\nCreated new files:")
    for p in output_files:
        print(p)
    print("\nExisting strategy, signals, backtest results, and GBPUSD model were not modified.")
    print("Scores remain experimental; legacy labels/timestamps are not independently validated.")


if __name__ == "__main__":
    main()
