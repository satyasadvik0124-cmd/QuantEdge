"""
Add experimental Random Forest confidence scores to a COPY of existing GBPUSD M15 SMC trade records.

Reads:
  data/GBPUSD_M15_2Y.csv
  outputs/backtest_results_v1.csv
  outputs/ml/rf_legacy_model.joblib
  outputs/ml/rf_legacy_model_features.json

Writes only:
  outputs/ml/smc_signals_with_ml_confidence.csv
  outputs/ml/smc_signals_scoring_report.txt

This script does NOT change the SMC strategy, entries, SL/TP, RR, or original backtest file.

IMPORTANT:
The saved model was trained on legacy labels with known timestamp-alignment limitations.
The score is an experimental model estimate, NOT a calibrated probability of future profitability.
This first pass scores the existing historical records; it is not a live-signal integration.
"""

from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CANDLES_FILE = ROOT / "data" / "GBPUSD_M15_2Y.csv"
SIGNALS_FILE = ROOT / "outputs" / "backtest_results_v1.csv"
MODEL_FILE = ROOT / "outputs" / "ml" / "rf_legacy_model.joblib"
SCHEMA_FILE = ROOT / "outputs" / "ml" / "rf_legacy_model_features.json"
OUTDIR = ROOT / "outputs" / "ml"
OUTPUT_FILE = OUTDIR / "smc_signals_with_ml_confidence.csv"
REPORT_FILE = OUTDIR / "smc_signals_scoring_report.txt"

BAR_MINUTES = 15
MIN_HISTORY = 60


def find_column(df, candidates, label):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    raise ValueError(
        f"Could not find {label} column. Available columns: {df.columns.tolist()}"
    )


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

    up_move = c["high"].diff()
    down_move = -c["low"].diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=c.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=c.index,
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
    for path in [CANDLES_FILE, SIGNALS_FILE, MODEL_FILE, SCHEMA_FILE]:
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    raw = pd.read_csv(CANDLES_FILE)
    signals = pd.read_csv(SIGNALS_FILE)
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    required_features = schema.get("features", [])
    if not required_features:
        raise ValueError("The model feature schema has an empty 'features' list.")

    time_col = find_column(raw, ["time", "datetime", "date", "timestamp"], "candle timestamp")
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

    required_signal_cols = {"signal_time", "direction", "entry", "sl", "tp"}
    missing = required_signal_cols - set(signals.columns)
    if missing:
        raise ValueError(f"Existing signal file is missing columns: {sorted(missing)}")

    signals["signal_time"] = pd.to_datetime(signals["signal_time"], errors="coerce")
    signals["direction"] = signals["direction"].astype(str).str.upper().str.strip()
    for col in ["entry", "sl", "tp"]:
        signals[col] = pd.to_numeric(signals[col], errors="coerce")

    feature_records = []
    for row_idx, signal in signals.iterrows():
        signal_time = signal["signal_time"]
        rec = {"_row_id": row_idx, "ml_feature_status": "OK"}

        if pd.isna(signal_time):
            rec["ml_feature_status"] = "INVALID_SIGNAL_TIME"
            feature_records.append(rec)
            continue

        # Match the training dataset: only use candles fully closed by signal_time.
        eligible = candles[candles["time"] + pd.Timedelta(minutes=BAR_MINUTES) <= signal_time]
        if eligible.empty:
            rec["ml_feature_status"] = "NO_COMPLETED_CANDLE_BEFORE_SIGNAL"
            feature_records.append(rec)
            continue

        candle = eligible.iloc[-1]
        rec["ml_feature_candle_time"] = candle["time"]
        if len(eligible) < MIN_HISTORY:
            rec["ml_feature_status"] = "INSUFFICIENT_HISTORY"

        # Technical features, using the same definitions as the training dataset.
        technical_names = [
            "rsi_14", "macd_atr", "macd_hist_atr", "ema9_vs_ema21_atr",
            "ema21_vs_ema50_atr", "close_vs_ema9_atr", "atr_14", "adx_14",
            "bb_position", "return_1", "return_4", "return_16",
            "candle_body_ratio", "candle_direction",
        ]
        for name in technical_names:
            rec[name] = candle.get(name, np.nan)

        direction = signal["direction"]
        entry, sl, tp = signal["entry"], signal["sl"], signal["tp"]
        rec["direction_buy"] = int(direction == "BUY")
        if pd.notna(entry) and pd.notna(sl):
            risk_distance = entry - sl if direction == "BUY" else sl - entry
        else:
            risk_distance = np.nan
        rec["risk_distance"] = risk_distance
        rec["risk_distance_atr"] = (
            risk_distance / candle["atr_14"]
            if pd.notna(risk_distance) and pd.notna(candle["atr_14"]) and candle["atr_14"] != 0
            else np.nan
        )
        if pd.notna(risk_distance) and risk_distance > 0 and pd.notna(entry) and pd.notna(tp):
            rec["target_rr_from_prices"] = (
                (tp - entry) / risk_distance if direction == "BUY"
                else (entry - tp) / risk_distance
            )
        else:
            rec["target_rr_from_prices"] = np.nan

        feature_records.append(rec)

    feature_df = pd.DataFrame(feature_records)
    scored = signals.copy()
    scored["_row_id"] = np.arange(len(scored))
    scored = scored.merge(feature_df, on="_row_id", how="left", validate="one_to_one")
    scored.drop(columns=["_row_id"], inplace=True)

    # Build the exact feature matrix saved alongside the trained model.
    X = pd.DataFrame(index=scored.index)
    for feature in required_features:
        if feature not in scored.columns:
            # Stop rather than silently inventing a feature definition.
            raise ValueError(
                f"Required model feature '{feature}' was not generated. "
                "Review the saved schema and feature-building logic."
            )
        X[feature] = pd.to_numeric(scored[feature], errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)

    model = joblib.load(MODEL_FILE)
    eligible_mask = scored["ml_feature_status"].eq("OK")
    scored["ml_estimated_win_score"] = np.nan
    scored["ml_predicted_class"] = pd.NA

    if eligible_mask.any():
        probabilities = model.predict_proba(X.loc[eligible_mask])
        classes = list(model.named_steps["model"].classes_)
        win_idx = classes.index(1)
        win_scores = probabilities[:, win_idx]
        scored.loc[eligible_mask, "ml_estimated_win_score"] = win_scores
        predicted = model.predict(X.loc[eligible_mask]).astype(int)
        scored.loc[eligible_mask, "ml_predicted_class"] = predicted

    scored["ml_estimated_win_score_pct"] = scored["ml_estimated_win_score"] * 100
    scored["ml_score_warning"] = (
        "Experimental score from legacy-label model; not a calibrated future-win probability."
    )

    # Save to a new file only; never overwrite the original backtest results.
    OUTDIR.mkdir(parents=True, exist_ok=True)
    scored.to_csv(OUTPUT_FILE, index=False)

    scoreable = scored["ml_estimated_win_score"].notna()
    lines = [
        "SMC SIGNAL ML CONFIDENCE SCORING — EXPERIMENTAL",
        "=" * 56,
        "Original strategy/backtest files were not modified.",
        "Scores are not calibrated real-world probabilities; legacy labels have timing limitations.",
        "This first pass scores historical records in backtest_results_v1.csv, not live signals.",
        "",
        f"Input signals: {len(signals)}",
        f"Scored records: {int(scoreable.sum())}",
        f"Unscored records: {int((~scoreable).sum())}",
        f"Feature status counts: {scored['ml_feature_status'].value_counts(dropna=False).to_dict()}",
    ]
    if scoreable.any():
        lines.extend([
            f"Mean estimated win score: {scored.loc[scoreable, 'ml_estimated_win_score'].mean():.4f}",
            f"Median estimated win score: {scored.loc[scoreable, 'ml_estimated_win_score'].median():.4f}",
            f"Scores >= 50% (experimental threshold only): {int((scored.loc[scoreable, 'ml_estimated_win_score'] >= 0.5).sum())}",
        ])
    lines.extend([
        "",
        f"Output CSV: {OUTPUT_FILE}",
        f"Report: {REPORT_FILE}",
    ])
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
