"""
Experimental ML scorer for existing QuantEdge SMC signals.
Does not modify strategy logic, model files, backtest outputs, or signal prices.
Scores are not calibrated probabilities because legacy labels/timestamps are unvalidated.
"""
from pathlib import Path
from datetime import datetime
import json
import joblib
import numpy as np
import pandas as pd

# Reuse the exact feature calculations from the existing legacy dataset builder.
from prepare_technical_dataset import build_features, find_column

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "GBPUSD_M15_2Y.csv"
SIGNALS_FILE = BASE_DIR / "outputs" / "signals_v3.csv"
MODEL_FILE = BASE_DIR / "outputs" / "ml" / "rf_legacy_model.joblib"
SCHEMA_FILE = BASE_DIR / "outputs" / "ml" / "rf_legacy_model_features.json"
OUTPUT_DIR = BASE_DIR / "outputs" / "ml"
BAR_MINUTES = 15
MIN_HISTORY = 60


def load_candles():
    raw = pd.read_csv(DATA_FILE)
    tc = find_column(raw, ["time", "datetime", "date", "timestamp"], "timestamp")
    oc = find_column(raw, ["open", "o"], "open")
    hc = find_column(raw, ["high", "h"], "high")
    lc = find_column(raw, ["low", "l"], "low")
    cc = find_column(raw, ["close", "c"], "close")
    candles = pd.DataFrame({
        "time": pd.to_datetime(raw[tc], errors="coerce"),
        "open": pd.to_numeric(raw[oc], errors="coerce"),
        "high": pd.to_numeric(raw[hc], errors="coerce"),
        "low": pd.to_numeric(raw[lc], errors="coerce"),
        "close": pd.to_numeric(raw[cc], errors="coerce"),
    })
    candles = (candles.dropna().sort_values("time")
               .drop_duplicates("time", keep="last").reset_index(drop=True))
    return build_features(candles)


def main():
    for p in (DATA_FILE, SIGNALS_FILE, MODEL_FILE, SCHEMA_FILE):
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    with SCHEMA_FILE.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    feature_cols = schema["features"]
    model = joblib.load(MODEL_FILE)
    candles = load_candles()
    raw = pd.read_csv(SIGNALS_FILE)

    tc = find_column(raw, ["signal_time", "time", "datetime"], "signal time")
    dc = find_column(raw, ["direction", "side", "signal"], "direction")
    ec = find_column(raw, ["entry", "entry_price"], "entry price")
    sc = find_column(raw, ["sl", "stop_loss", "stoploss"], "stop loss")
    pc = find_column(raw, ["tp", "take_profit", "takeprofit"], "take profit")

    signals = raw.copy()
    signals["signal_time"] = pd.to_datetime(signals[tc], errors="coerce")
    signals["direction"] = signals[dc].astype(str).str.upper().str.strip()
    signals["entry"] = pd.to_numeric(signals[ec], errors="coerce")
    signals["sl"] = pd.to_numeric(signals[sc], errors="coerce")
    signals["tp"] = pd.to_numeric(signals[pc], errors="coerce")

    rows = []
    for _, sig in signals.iterrows():
        out = sig.to_dict()
        out.update({
            "ml_feature_candle_time": pd.NaT,
            "ml_feature_status": "NOT_SCORED",
            "ml_estimated_win_score": np.nan,
            "ml_estimated_win_score_pct": np.nan,
            "ml_predicted_class": np.nan,
            "ml_score_warning": "Experimental legacy-model score; not a calibrated win probability.",
        })
        t, direction = sig["signal_time"], sig["direction"]
        entry, sl = sig["entry"], sig["sl"]

        if pd.isna(t):
            out["ml_feature_status"] = "INVALID_SIGNAL_TIME"
            rows.append(out)
            continue
        if direction not in ("BUY", "SELL"):
            out["ml_feature_status"] = "INVALID_DIRECTION"
            rows.append(out)
            continue
        if pd.isna(entry) or pd.isna(sl):
            out["ml_feature_status"] = "INVALID_ENTRY_OR_SL"
            rows.append(out)
            continue

        # Match training convention: candles are timestamped at open;
        # only use candles fully closed by the signal timestamp.
        eligible = candles[candles["time"] + pd.Timedelta(minutes=BAR_MINUTES) <= t]
        if eligible.empty:
            out["ml_feature_status"] = "NO_COMPLETED_CANDLE_BEFORE_SIGNAL"
            rows.append(out)
            continue
        candle = eligible.iloc[-1]
        out["ml_feature_candle_time"] = candle["time"]
        if len(eligible) < MIN_HISTORY:
            out["ml_feature_status"] = "INSUFFICIENT_HISTORY"
            rows.append(out)
            continue

        values = {col: candle.get(col, np.nan) for col in feature_cols}
        risk = entry - sl if direction == "BUY" else sl - entry
        values["direction_buy"] = int(direction == "BUY")
        values["risk_distance"] = risk
        atr = candle.get("atr_14", np.nan)
        values["risk_distance_atr"] = risk / atr if pd.notna(atr) and atr != 0 else np.nan

        X = pd.DataFrame([[values.get(col, np.nan) for col in feature_cols]],
                         columns=feature_cols).apply(pd.to_numeric, errors="coerce")
        if not np.isfinite(X.to_numpy(dtype=float)).all():
            out["ml_feature_status"] = "MISSING_OR_NONFINITE_FEATURES"
            rows.append(out)
            continue
        try:
            probs = model.predict_proba(X)[0]
            classes = list(model.classes_)
            if 1 not in classes:
                out["ml_feature_status"] = "MODEL_HAS_NO_POSITIVE_CLASS"
                rows.append(out)
                continue
            score = float(probs[classes.index(1)])
            out["ml_estimated_win_score"] = score
            out["ml_estimated_win_score_pct"] = round(score * 100, 2)
            out["ml_predicted_class"] = int(model.predict(X)[0])
            out["ml_feature_status"] = "OK"
        except Exception as exc:
            out["ml_feature_status"] = f"MODEL_SCORING_ERROR: {type(exc).__name__}"
        rows.append(out)

    result = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = OUTPUT_DIR / f"live_smc_signal_scores_{stamp}.csv"
    result.to_csv(output, index=False)
    print("\n===== QUANTEDGE SMC ML SCORING =====")
    print(f"Signals read: {len(result):,}")
    print("\nScoring status:")
    print(result["ml_feature_status"].value_counts(dropna=False).to_string())
    print(f"\nSaved to: {output}")
    print("Existing strategy, signal prices, SL/TP, RR, model, and backtest files were not modified.")
    print("Scores are experimental and must not be interpreted as calibrated probabilities.")


if __name__ == "__main__":
    main()
