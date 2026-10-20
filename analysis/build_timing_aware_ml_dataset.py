"""
Build a separate, timing-aware ML dataset for GBPUSD M15 SMC trades.

This script DOES NOT modify existing strategy files or backtest_results_v1.csv.
It creates:
  outputs/ml/gbpusd_m15_timing_audit.csv
  outputs/ml/gbpusd_m15_timing_audit_summary.txt

Important:
- Component matching is heuristic because the source files do not share setup IDs.
- Ambiguous or unmatched trades are flagged; do not treat this as validated model data yet.
- Uses only completed candles available by the estimated setup availability time.
- Outcome is recomputed after the original entry is first touched after availability.
- If SL and TP are both hit in the same M15 candle, SL is assumed first (conservative).
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "GBPUSD_M15_2Y.csv"
TRADES = ROOT / "outputs" / "backtest_results_v1.csv"
SWEEPS = ROOT / "outputs" / "validated_sweeps_v2.csv"
OBS = ROOT / "outputs" / "order_blocks_v1.csv"
FVGS = ROOT / "outputs" / "fvg_v2.csv"
OUTDIR = ROOT / "outputs" / "ml"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "gbpusd_m15_timing_audit.csv"
SUMMARY = OUTDIR / "gbpusd_m15_timing_audit_summary.txt"

BAR_MINUTES = 15
MAX_COMPONENT_DAYS = 7

def load_time_csv(path, col="time"):
    d = pd.read_csv(path)
    d[col] = pd.to_datetime(d[col], errors="coerce")
    return d.dropna(subset=[col]).sort_values(col).reset_index(drop=True)

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calculate_features(c):
    close, high, low = c["close"], c["high"], c["low"]
    prev_close = close.shift(1)
    tr = pd.concat([(high-low), (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    c["ema_9"] = close.ewm(span=9, adjust=False).mean()
    c["ema_21"] = close.ewm(span=21, adjust=False).mean()
    c["ema_50"] = close.ewm(span=50, adjust=False).mean()
    c["rsi_14"] = rsi(close, 14)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    c["macd"] = ema12 - ema26
    c["macd_signal"] = c["macd"].ewm(span=9, adjust=False).mean()
    c["macd_hist"] = c["macd"] - c["macd_signal"]
    c["atr_14"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / c["atr_14"].replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / c["atr_14"].replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    c["adx_14"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    c["bb_mid_20"] = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    c["bb_upper_20"] = c["bb_mid_20"] + 2 * bb_std
    c["bb_lower_20"] = c["bb_mid_20"] - 2 * bb_std
    c["bb_position"] = (close - c["bb_lower_20"]) / (c["bb_upper_20"] - c["bb_lower_20"]).replace(0, np.nan)
    c["return_1"] = close.pct_change(1)
    c["return_4"] = close.pct_change(4)
    c["return_16"] = close.pct_change(16)
    candle_range = (high-low).replace(0, np.nan)
    c["body_range_ratio"] = (close-c["open"]).abs() / candle_range
    c["candle_direction"] = np.sign(close-c["open"])
    c["ema_9_21_gap_atr"] = (c["ema_9"]-c["ema_21"]) / c["atr_14"].replace(0, np.nan)
    c["ema_21_50_gap_atr"] = (c["ema_21"]-c["ema_50"]) / c["atr_14"].replace(0, np.nan)
    return c

def first_or_none(df):
    return None if df.empty else df.iloc[0]

candles = load_time_csv(DATA, "time")
for col in ["open", "high", "low", "close", "tick_volume", "spread"]:
    candles[col] = pd.to_numeric(candles[col], errors="coerce")
candles = candles.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
candles = calculate_features(candles)

trades = load_time_csv(TRADES, "signal_time")
sweeps = load_time_csv(SWEEPS, "sweep_time")
sweeps["choch_time"] = pd.to_datetime(sweeps["choch_time"], errors="coerce")
obs = load_time_csv(OBS, "time")
fvgs = load_time_csv(FVGS, "time")

feature_cols = [
    "rsi_14", "macd", "macd_signal", "macd_hist", "ema_9", "ema_21", "ema_50",
    "atr_14", "adx_14", "bb_position", "return_1", "return_4", "return_16",
    "body_range_ratio", "candle_direction", "ema_9_21_gap_atr", "ema_21_50_gap_atr"
]
records = []
for _, tr in trades.iterrows():
    direction = str(tr["direction"]).upper()
    ob_type = "BULLISH_OB" if direction == "BUY" else "BEARISH_OB"
    sweep_type = "SSL_SWEEP" if direction == "BUY" else "BSL_SWEEP"
    fvg_type = "BULLISH_FVG" if direction == "BUY" else "BEARISH_FVG"
    ob_time = pd.Timestamp(tr["signal_time"])

    ob_candidates = obs[
        (obs["type"] == ob_type) &
        ((obs["time"] - ob_time).abs() <= pd.Timedelta(minutes=BAR_MINUTES))
    ]
    ob = first_or_none(ob_candidates)
    row = {
        "legacy_signal_time": ob_time,
        "direction": direction,
        "entry": float(tr["entry"]),
        "sl": float(tr["sl"]),
        "tp": float(tr["tp"]),
        "legacy_result": str(tr["result"]).upper(),
        "legacy_rr": float(tr["rr"]),
        "matched_ob_time": pd.NaT,
        "matched_sweep_time": pd.NaT,
        "matched_choch_time": pd.NaT,
        "matched_fvg_time": pd.NaT,
        "estimated_available_time": pd.NaT,
        "component_match_status": "",
        "entry_reached_after_availability": False,
        "entry_time": pd.NaT,
        "aligned_result": "",
        "target_tp_first": np.nan,
        "bars_to_entry": np.nan,
        "bars_to_outcome": np.nan,
    }
    if ob is None:
        row["component_match_status"] = "NO_EXACT_DIRECTIONAL_OB"
        records.append(row)
        continue

    row["matched_ob_time"] = ob["time"]
    horizon = pd.Timedelta(days=MAX_COMPONENT_DAYS)
    sw = sweeps[
        (sweeps["type"] == sweep_type) &
        (sweeps["sweep_time"] >= ob_time - horizon) &
        (sweeps["sweep_time"] <= ob_time + horizon) &
        (sweeps["choch_time"] >= ob_time) &
        (sweeps["choch_time"] >= sweeps["sweep_time"])
    ].copy()
    if sw.empty:
        row["component_match_status"] = "NO_MATCHING_SWEEP_CHOCH"
        records.append(row)
        continue
    sw["distance"] = (sw["choch_time"] - ob_time).abs()
    sw = sw.sort_values(["distance", "choch_time"])
    sweep = sw.iloc[0]
    row["matched_sweep_time"] = sweep["sweep_time"]
    row["matched_choch_time"] = sweep["choch_time"]

    fg = fvgs[
        (fvgs["type"] == fvg_type) &
        (fvgs["time"] >= ob_time) &
        (fvgs["time"] <= ob_time + horizon)
    ].copy()
    if fg.empty:
        row["component_match_status"] = "NO_MATCHING_FVG"
        records.append(row)
        continue
    fg["distance"] = (fg["time"] - sweep["choch_time"]).abs()
    fvg = fg.sort_values(["distance", "time"]).iloc[0]
    row["matched_fvg_time"] = fvg["time"]

    # CSV candle times are assumed to be candle-open timestamps.
    available = max(ob_time, sweep["sweep_time"], sweep["choch_time"], fvg["time"]) + pd.Timedelta(minutes=BAR_MINUTES)
    row["estimated_available_time"] = available
    row["component_match_status"] = "HEURISTIC_MATCH"

    # Use the latest fully completed candle at availability time for features.
    feat_idx = candles.index[candles["time"] + pd.Timedelta(minutes=BAR_MINUTES) <= available]
    if len(feat_idx):
        feat = candles.loc[feat_idx[-1]]
        for fc in feature_cols:
            row[fc] = feat[fc]
        row["feature_candle_time"] = feat["time"]
        row["signal_direction_flag"] = 1 if direction == "BUY" else -1
        row["risk_distance"] = abs(float(tr["entry"]) - float(tr["sl"]))
        row["risk_distance_atr"] = row["risk_distance"] / feat["atr_14"] if pd.notna(feat["atr_14"]) and feat["atr_14"] != 0 else np.nan
        row["feature_status"] = "OK" if all(pd.notna(row.get(fc, np.nan)) for fc in feature_cols) else "MISSING_FEATURES"
    else:
        row["feature_status"] = "NO_COMPLETED_FEATURE_CANDLE"

    # Entry must be touched after the estimated availability time.
    future = candles[candles["time"] >= available].copy().reset_index(drop=True)
    entry = float(tr["entry"])
    sl, tp = float(tr["sl"]), float(tr["tp"])
    touched = future[(future["low"] <= entry) & (future["high"] >= entry)]
    if touched.empty:
        row["entry_reached_after_availability"] = False
        row["aligned_result"] = "NO_FUTURE_ENTRY_TOUCH"
        records.append(row)
        continue

    entry_time = touched.iloc[0]["time"]
    row["entry_reached_after_availability"] = True
    row["entry_time"] = entry_time
    row["bars_to_entry"] = int(future.index[future["time"] == entry_time][0]) + 1
    entry_candle = future[future["time"] == entry_time].iloc[0]
    if direction == "BUY":
        entry_candle_hit_sl = entry_candle["low"] <= sl
        entry_candle_hit_tp = entry_candle["high"] >= tp
    else:
        entry_candle_hit_sl = entry_candle["high"] >= sl
        entry_candle_hit_tp = entry_candle["low"] <= tp

    # OHLC data cannot reveal whether SL/TP was touched before or after entry
    # inside the entry candle. Flag this rather than inventing an outcome.
    if entry_candle_hit_sl or entry_candle_hit_tp:
        row["aligned_result"] = "ENTRY_CANDLE_AMBIGUOUS"
        row["bars_to_outcome"] = 1
        records.append(row)
        continue

    after_entry = future[future["time"] > entry_time].reset_index(drop=True)
    outcome = "UNRESOLVED"
    outcome_bars = np.nan
    for j, candle in after_entry.iterrows():
        if direction == "BUY":
            hit_sl = candle["low"] <= sl
            hit_tp = candle["high"] >= tp
        else:
            hit_sl = candle["high"] >= sl
            hit_tp = candle["low"] <= tp
        if hit_sl and hit_tp:
            outcome = "LOSS_SAME_CANDLE_AMBIGUOUS_SL_FIRST"
            outcome_bars = j + 2
            break
        if hit_sl:
            outcome = "LOSS"
            outcome_bars = j + 2
            break
        if hit_tp:
            outcome = "WIN"
            outcome_bars = j + 2
            break
    row["aligned_result"] = outcome
    row["bars_to_outcome"] = outcome_bars
    if outcome == "WIN":
        row["target_tp_first"] = 1
    elif outcome.startswith("LOSS"):
        row["target_tp_first"] = 0
    records.append(row)

out = pd.DataFrame(records)
out.to_csv(OUT, index=False)
summary = []
summary.append("TIMING-AWARE ML DATASET AUDIT")
summary.append(f"Legacy trades: {len(out)}")
summary.append(f"Component status:\n{out['component_match_status'].value_counts(dropna=False).to_string()}")
summary.append(f"\nFeature status:\n{out.get('feature_status', pd.Series(dtype=str)).value_counts(dropna=False).to_string()}")
summary.append(f"\nEntry touched after availability: {int(out['entry_reached_after_availability'].fillna(False).sum())}")
summary.append(f"\nAligned outcome status:\n{out['aligned_result'].value_counts(dropna=False).to_string()}")
summary.append(f"\nLegacy outcomes:\n{out['legacy_result'].value_counts(dropna=False).to_string()}")
summary.append("\nCAUTION: Component matching is heuristic and requires manual validation. This is an audit dataset, not yet a validated ML benchmark.")
SUMMARY.write_text("\n".join(summary), encoding="utf-8")
print("\n".join(summary))
print(f"\nSaved audit CSV: {OUT}")
print(f"Saved summary: {SUMMARY}")
