"""
Prepare a technical-indicator feature dataset for the existing GBPUSD M15 SMC trades.

This script does NOT modify the existing backtest or SMC outputs.
It uses only completed candles available at the signal timestamp (assuming CSV
timestamps denote candle-open times) and joins the existing V1 WIN/LOSS labels.

IMPORTANT RESEARCH LIMITATION:
The V1 signals were found to have potentially premature timestamps. Therefore,
this output is a LEGACY BASELINE DATASET for pipeline development, not a
validated dataset for claiming predictive performance. The old WIN/LOSS labels
come from the old entry assumptions. Do not interpret model scores as reliable
probabilities until signal timing and trade outcomes are aligned.
"""

from pathlib import Path
import numpy as np
import pandas as pd

# -----------------------------
# Paths and settings
# -----------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "GBPUSD_M15_2Y.csv"
TRADES_FILE = BASE_DIR / "outputs" / "backtest_results_v1.csv"
OUTPUT_DIR = BASE_DIR / "outputs" / "ml"
OUTPUT_FILE = OUTPUT_DIR / "gbpusd_m15_technical_features_legacy.csv"

BAR_MINUTES = 15
MIN_HISTORY = 60


def find_column(df, candidates, label, required=True):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    if required:
        raise ValueError(
            f"Could not find {label} column. Available columns: {df.columns.tolist()}"
        )
    return None


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    out = out.mask((avg_loss == 0) & (avg_gain > 0), 100)
    out = out.mask((avg_gain == 0) & (avg_loss > 0), 0)
    return out


def build_features(candles):
    c = candles.copy()
    c["ema_9"] = c["close"].ewm(span=9, adjust=False).mean()
    c["ema_21"] = c["close"].ewm(span=21, adjust=False).mean()
    c["ema_50"] = c["close"].ewm(span=50, adjust=False).mean()
    c["rsi_14"] = rsi(c["close"], 14)

    ema12 = c["close"].ewm(span=12, adjust=False).mean()
    ema26 = c["close"].ewm(span=26, adjust=False).mean()
    c["macd"] = ema12 - ema26
    c["macd_signal"] = c["macd"].ewm(span=9, adjust=False).mean()
    c["macd_hist"] = c["macd"] - c["macd_signal"]

    prev_close = c["close"].shift(1)
    tr = pd.concat([
        c["high"] - c["low"],
        (c["high"] - prev_close).abs(),
        (c["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    c["atr_14"] = tr.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    # ADX (Wilder-style smoothing approximation)
    up_move = c["high"].diff()
    down_move = -c["low"].diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=c.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=c.index
    )
    atr_safe = c["atr_14"].replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr_safe
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr_safe
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    c["adx_14"] = dx.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    c["bb_mid_20"] = c["close"].rolling(20).mean()
    bb_std = c["close"].rolling(20).std()
    c["bb_upper_20"] = c["bb_mid_20"] + 2 * bb_std
    c["bb_lower_20"] = c["bb_mid_20"] - 2 * bb_std
    band_width = (c["bb_upper_20"] - c["bb_lower_20"]).replace(0, np.nan)
    c["bb_position"] = (c["close"] - c["bb_lower_20"]) / band_width

    c["return_1"] = c["close"].pct_change(1)
    c["return_4"] = c["close"].pct_change(4)
    c["return_16"] = c["close"].pct_change(16)
    candle_range = (c["high"] - c["low"]).replace(0, np.nan)
    c["candle_body_ratio"] = (c["close"] - c["open"]).abs() / candle_range
    c["candle_direction"] = np.sign(c["close"] - c["open"])
    c["close_vs_ema9_atr"] = (c["close"] - c["ema_9"]) / c["atr_14"]
    c["ema9_vs_ema21_atr"] = (c["ema_9"] - c["ema_21"]) / c["atr_14"]
    c["ema21_vs_ema50_atr"] = (c["ema_21"] - c["ema_50"]) / c["atr_14"]
    c["macd_atr"] = c["macd"] / c["atr_14"]
    c["macd_hist_atr"] = c["macd_hist"] / c["atr_14"]
    return c


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Historical candle file not found: {DATA_FILE}")
    if not TRADES_FILE.exists():
        raise FileNotFoundError(f"Existing V1 results not found: {TRADES_FILE}")

    raw = pd.read_csv(DATA_FILE)
    trades = pd.read_csv(TRADES_FILE)

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
    candles = build_features(candles)

    required_trade_cols = {"signal_time", "direction", "entry", "sl", "tp", "result"}
    missing = required_trade_cols - set(trades.columns)
    if missing:
        raise ValueError(f"Trade results missing columns: {sorted(missing)}")

    trades["signal_time"] = pd.to_datetime(trades["signal_time"], errors="coerce")
    trades["direction"] = trades["direction"].astype(str).str.upper().str.strip()
    trades["result"] = trades["result"].astype(str).str.upper().str.strip()
    trades["entry"] = pd.to_numeric(trades["entry"], errors="coerce")
    trades["sl"] = pd.to_numeric(trades["sl"], errors="coerce")
    trades["tp"] = pd.to_numeric(trades["tp"], errors="coerce")
    trades["trade_id"] = np.arange(len(trades))

    feature_cols = [
        "rsi_14", "macd_atr", "macd_hist_atr", "ema9_vs_ema21_atr",
        "ema21_vs_ema50_atr", "close_vs_ema9_atr", "atr_14", "adx_14",
        "bb_position", "return_1", "return_4", "return_16",
        "candle_body_ratio", "candle_direction",
    ]

    # As timestamps are assumed to denote candle OPEN, only use candles whose
    # close time (open timestamp + 15 min) is <= the signal timestamp.
    feature_rows = []
    for _, trade in trades.iterrows():
        signal_time = trade["signal_time"]
        if pd.isna(signal_time):
            continue
        eligible = candles[candles["time"] + pd.Timedelta(minutes=BAR_MINUTES) <= signal_time]
        if eligible.empty:
            feature_rows.append({
                "trade_id": trade["trade_id"],
                "feature_candle_time": pd.NaT,
                "feature_status": "NO_COMPLETED_CANDLE_BEFORE_SIGNAL",
            })
            continue

        row = eligible.iloc[-1]
        out = {
            "trade_id": trade["trade_id"],
            "feature_candle_time": row["time"],
            "feature_status": "OK" if len(eligible) >= MIN_HISTORY else "INSUFFICIENT_HISTORY",
        }
        for col in feature_cols:
            out[col] = row[col]
        feature_rows.append(out)

    features = pd.DataFrame(feature_rows)
    dataset = trades.merge(features, on="trade_id", how="left")
    dataset["direction_buy"] = (dataset["direction"] == "BUY").astype(int)
    dataset["risk_distance"] = np.where(
        dataset["direction"] == "BUY",
        dataset["entry"] - dataset["sl"],
        dataset["sl"] - dataset["entry"],
    )
    dataset["risk_distance_atr"] = dataset["risk_distance"] / dataset["atr_14"].replace(0, np.nan)
    dataset["target_rr_from_prices"] = np.where(
        dataset["risk_distance"] > 0,
        np.where(
            dataset["direction"] == "BUY",
            (dataset["tp"] - dataset["entry"]) / dataset["risk_distance"],
            (dataset["entry"] - dataset["tp"]) / dataset["risk_distance"],
        ),
        np.nan,
    )

    # Label only settled WIN/LOSS records. This preserves original V1 labels.
    dataset["target_tp_first"] = dataset["result"].map({"WIN": 1, "LOSS": 0})
    dataset["label_source"] = "backtest_results_v1.csv"
    dataset["dataset_warning"] = (
        "LEGACY LABELS: V1 signal timestamps were flagged by timing audit; "
        "not suitable for validated predictive claims until outcomes are re-aligned."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT_FILE, index=False)

    print("\n===== TECHNICAL FEATURE DATASET =====")
    print(f"Candles loaded: {len(candles):,}")
    print(f"Legacy trades loaded: {len(trades):,}")
    print(f"Rows written: {len(dataset):,}")
    print(f"WIN labels: {(dataset['target_tp_first'] == 1).sum():,}")
    print(f"LOSS labels: {(dataset['target_tp_first'] == 0).sum():,}")
    print(f"Missing/invalid labels: {dataset['target_tp_first'].isna().sum():,}")
    if "feature_status" in dataset:
        print("\nFeature status:")
        print(dataset["feature_status"].value_counts(dropna=False).to_string())
    print(f"\nSaved: {OUTPUT_FILE}")
    print("\nWARNING: This is a legacy baseline feature table, not yet a validated ML training set.")
    print("Do not train/evaluate a model for performance claims until labels and actionable timestamps are aligned.")


if __name__ == "__main__":
    main()
