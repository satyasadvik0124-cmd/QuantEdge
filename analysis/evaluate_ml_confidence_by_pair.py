"""
QuantEdge: evaluate saved ML confidence scores against existing Entry-Touch outcomes.
Run from project root:
    python .\analysis\evaluate_ml_confidence_by_pair.py

This script writes new reports under outputs/ml/confidence_evaluation/.
It does not edit strategy, signals, models, or existing backtest files.
"""
from pathlib import Path
import json
import warnings
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "ml" / "confidence_evaluation"
BAR_MINUTES = 15
MIN_HISTORY = 60

PAIRS = {
    "GBPUSD": {
        "candles": ROOT / "data" / "GBPUSD_M15_5Y.csv",
        "signals": ROOT / "outputs/multi_pair_5y/GBPUSD/full_available/outputs/signals_v3.csv",
        "comparison": ROOT / "outputs/ml/gbpusd_same_signals_method_comparison.csv",
        "model": ROOT / "outputs/ml/rf_legacy_model.joblib",
        "schema": ROOT / "outputs/ml/rf_legacy_model_features.json",
    },
    "XAUUSD": {
        "candles": ROOT / "data" / "XAUUSD_M15_5Y.csv",
        "signals": ROOT / "outputs/multi_pair_5y/XAUUSD/full_available/outputs/signals_v3.csv",
        "comparison": ROOT / "outputs/ml/xauusd_same_signals_method_comparison.csv",
        "model": ROOT / "outputs/ml/xauusd_rf_model.joblib",
        "schema": ROOT / "outputs/ml/xauusd_rf_model_features.json",
    },
}
TECHNICAL = [
    "rsi_14", "macd_atr", "macd_hist_atr", "ema9_vs_ema21_atr",
    "ema21_vs_ema50_atr", "close_vs_ema9_atr", "atr_14", "adx_14",
    "bb_position", "return_1", "return_4", "return_16",
    "candle_body_ratio", "candle_direction",
]
BANDS = ["<40%", "40–<50%", "50–<60%", "≥60%"]


def find_col(df, names, label):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    raise ValueError(f"Missing {label} column. Available: {df.columns.tolist()}")


def calc_rsi(s, n=14):
    d = s.diff()
    gain = d.clip(lower=0)
    loss = -d.clip(upper=0)
    ag = gain.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    al = loss.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out = out.mask((al == 0) & (ag > 0), 100)
    return out.mask((ag == 0) & (al > 0), 0)


def build_features(c):
    c = c.copy()
    c["ema_9"] = c.close.ewm(span=9, adjust=False).mean()
    c["ema_21"] = c.close.ewm(span=21, adjust=False).mean()
    c["ema_50"] = c.close.ewm(span=50, adjust=False).mean()
    c["rsi_14"] = calc_rsi(c.close)
    e12 = c.close.ewm(span=12, adjust=False).mean()
    e26 = c.close.ewm(span=26, adjust=False).mean()
    c["macd"] = e12 - e26
    c["macd_signal"] = c.macd.ewm(span=9, adjust=False).mean()
    c["macd_hist"] = c.macd - c.macd_signal
    prev = c.close.shift(1)
    tr = pd.concat([c.high-c.low, (c.high-prev).abs(), (c.low-prev).abs()], axis=1).max(axis=1)
    c["atr_14"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    up, down = c.high.diff(), -c.low.diff()
    plus = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=c.index)
    minus = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=c.index)
    atr = c.atr_14.replace(0, np.nan)
    pdi = 100 * plus.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr
    mdi = 100 * minus.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr
    dx = 100 * (pdi-mdi).abs() / (pdi+mdi).replace(0, np.nan)
    c["adx_14"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    mid = c.close.rolling(20).mean()
    sd = c.close.rolling(20).std()
    upper, lower = mid+2*sd, mid-2*sd
    c["bb_position"] = (c.close-lower) / (upper-lower).replace(0, np.nan)
    for n in (1, 4, 16):
        c[f"return_{n}"] = c.close.pct_change(n)
    rng = (c.high-c.low).replace(0, np.nan)
    c["candle_body_ratio"] = (c.close-c.open).abs()/rng
    c["candle_direction"] = np.sign(c.close-c.open)
    c["close_vs_ema9_atr"] = (c.close-c.ema_9)/c.atr_14
    c["ema9_vs_ema21_atr"] = (c.ema_9-c.ema_21)/c.atr_14
    c["ema21_vs_ema50_atr"] = (c.ema_21-c.ema_50)/c.atr_14
    c["macd_atr"] = c.macd/c.atr_14
    c["macd_hist_atr"] = c.macd_hist/c.atr_14
    return c


def load_candles(path):
    raw = pd.read_csv(path)
    cols = {x: find_col(raw, names, x) for x, names in {
        "time": ["time", "datetime", "date", "timestamp"],
        "open": ["open", "o"], "high": ["high", "h"],
        "low": ["low", "l"], "close": ["close", "c"],
    }.items()}
    c = pd.DataFrame({k: raw[v] for k, v in cols.items()})
    c["time"] = pd.to_datetime(c.time, errors="coerce")
    for col in ["open", "high", "low", "close"]:
        c[col] = pd.to_numeric(c[col], errors="coerce")
    c = c.dropna().sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    return build_features(c)


def get_classes(model):
    if hasattr(model, "classes_"):
        return list(model.classes_)
    if hasattr(model, "named_steps"):
        for estimator in reversed(list(model.named_steps.values())):
            if hasattr(estimator, "classes_"):
                return list(estimator.classes_)
    raise ValueError("Cannot determine class labels from saved model.")


def score_one(pair, cfg):
    for key in ("candles", "signals", "comparison", "model", "schema"):
        if not cfg[key].exists():
            raise FileNotFoundError(f"{pair}: missing {cfg[key]}")
    candles = load_candles(cfg["candles"])
    signals = pd.read_csv(cfg["signals"]).reset_index(drop=True)
    compare = pd.read_csv(cfg["comparison"])
    schema = json.loads(cfg["schema"].read_text(encoding="utf-8"))
    feature_cols = schema.get("features", [])
    if not feature_cols:
        raise ValueError(f"{pair}: feature list is empty.")
    signals["signal_id"] = np.arange(len(signals))
    signals["signal_time"] = pd.to_datetime(signals.signal_time, errors="coerce")
    signals["direction"] = signals.direction.astype(str).str.upper().str.strip()
    for col in ["entry", "sl", "tp"]:
        signals[col] = pd.to_numeric(signals[col], errors="coerce")

    model = joblib.load(cfg["model"])
    classes = get_classes(model)
    if 1 not in classes:
        raise ValueError(f"{pair}: model has no class 1.")
    win_idx = classes.index(1)
    recs = []
    for _, s in signals.iterrows():
        r = {"signal_id": int(s.signal_id), "ml_feature_status": "OK", "ml_feature_candle_time": pd.NaT}
        t, direction = s.signal_time, s.direction
        if pd.isna(t):
            r["ml_feature_status"] = "INVALID_SIGNAL_TIME"
            recs.append(r); continue
        if direction not in ("BUY", "SELL"):
            r["ml_feature_status"] = "INVALID_DIRECTION"
            recs.append(r); continue
        eligible = candles[candles.time + pd.Timedelta(minutes=BAR_MINUTES) <= t]
        if eligible.empty:
            r["ml_feature_status"] = "NO_COMPLETED_CANDLE_BEFORE_SIGNAL"
            recs.append(r); continue
        candle = eligible.iloc[-1]
        r["ml_feature_candle_time"] = candle.time
        if len(eligible) < MIN_HISTORY:
            r["ml_feature_status"] = "INSUFFICIENT_HISTORY"
            recs.append(r); continue
        for name in TECHNICAL:
            r[name] = candle.get(name, np.nan)
        risk = s.entry-s.sl if direction == "BUY" else s.sl-s.entry
        r["direction_buy"] = int(direction == "BUY")
        r["risk_distance"] = risk
        r["risk_distance_atr"] = risk/candle.atr_14 if pd.notna(candle.atr_14) and candle.atr_14 != 0 else np.nan
        recs.append(r)

    out = signals.merge(pd.DataFrame(recs), on="signal_id", how="left", validate="one_to_one")
    X = pd.DataFrame(index=out.index)
    for col in feature_cols:
        if col not in out.columns:
            raise ValueError(f"{pair}: feature {col!r} not constructed.")
        X[col] = pd.to_numeric(out[col], errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    valid = out.ml_feature_status.eq("OK") & X.notna().all(axis=1)
    out.loc[out.ml_feature_status.eq("OK") & ~X.notna().all(axis=1), "ml_feature_status"] = "MISSING_OR_NONFINITE_FEATURES"
    out["ml_estimated_win_score"] = np.nan
    if valid.any():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            prob = model.predict_proba(X.loc[valid])
        out.loc[valid, "ml_estimated_win_score"] = prob[:, win_idx]
    out["ml_estimated_win_score_pct"] = out.ml_estimated_win_score*100
    out["ml_score_warning"] = "Experimental score; not a calibrated future-win probability."

    if "signal_id" not in compare:
        raise ValueError(f"{pair}: comparison CSV lacks signal_id.")
    keep = [c for c in ["signal_id", "original_result", "entry_touch_result",
                         "entry_touch_time", "entry_touch_exit_time", "entry_touch_exit_reason"] if c in compare]
    compare = compare[keep].copy()
    compare["signal_id"] = pd.to_numeric(compare.signal_id, errors="coerce")
    out = out.merge(compare, on="signal_id", how="left", validate="one_to_one")
    out["entry_touch_result"] = out.entry_touch_result.astype(str).str.upper()
    out["entry_touch_R"] = np.select(
        [out.entry_touch_result.eq("WIN"), out.entry_touch_result.eq("LOSS")],
        [4.0, -1.0], default=np.nan
    )
    out["confidence_band"] = pd.cut(
        out.ml_estimated_win_score,
        bins=[-np.inf, .4, .5, .6, np.inf],
        labels=BANDS, right=False, include_lowest=True
    )

    def metrics(group, band):
        resolved = group[group.entry_touch_result.isin(["WIN", "LOSS"])].sort_values("signal_time")
        rr = resolved.entry_touch_R.astype(float)
        wins = int((resolved.entry_touch_result == "WIN").sum())
        losses = int((resolved.entry_touch_result == "LOSS").sum())
        gross_profit = float(rr[rr > 0].sum())
        gross_loss = float(-rr[rr < 0].sum())
        pf = gross_profit/gross_loss if gross_loss else (np.inf if gross_profit else np.nan)
        equity = rr.cumsum()
        dd = float((equity.cummax()-equity).max()) if len(equity) else 0.0
        return {
            "pair": pair, "confidence_band": band,
            "signals_scored": int(group.ml_estimated_win_score.notna().sum()),
            "resolved_trades": len(resolved), "wins": wins, "losses": losses,
            "win_rate_pct": round(100*wins/len(resolved), 2) if len(resolved) else np.nan,
            "net_R": round(float(rr.sum()), 2),
            "profit_factor": round(pf, 4) if np.isfinite(pf) else ("Infinity" if pf == np.inf else np.nan),
            "max_drawdown_R_trade_sequence": round(dd, 2),
            "unresolved_or_unmatched": int(len(group)-len(resolved)),
        }

    scoreable = out[out.ml_estimated_win_score.notna()]
    rows = [metrics(scoreable, "ALL SCORED (baseline)")]
    for band in BANDS:
        rows.append(metrics(scoreable[scoreable.confidence_band == band], band))
    summary = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    scored_path = OUT / f"{pair.lower()}_signals_with_ml_confidence.csv"
    summary_path = OUT / f"{pair.lower()}_confidence_band_summary.csv"
    out.to_csv(scored_path, index=False)
    summary.to_csv(summary_path, index=False)
    print(f"\n===== {pair} =====")
    print(f"Candles: {len(candles):,}; signals: {len(signals):,}")
    print("Feature statuses:\n" + out.ml_feature_status.value_counts(dropna=False).to_string())
    print(summary.to_string(index=False))
    print(f"Scored file: {scored_path}\nSummary: {summary_path}")
    return summary


def main():
    print("QuantEdge ML confidence evaluation. Existing Entry-Touch outcomes are reused.")
    print("No strategy rules, signal prices, SL/TP, RR, models, or existing backtests are changed.")
    print("Reminder: Entry-Touch skips SL/TP checks during the entry-touch candle.")
    summaries = [score_one(pair, cfg) for pair, cfg in PAIRS.items()]
    OUT.mkdir(parents=True, exist_ok=True)
    combined = pd.concat(summaries, ignore_index=True)
    path = OUT / "all_pairs_confidence_band_summary.csv"
    combined.to_csv(path, index=False)
    print(f"\nCombined summary: {path}")


if __name__ == "__main__":
    main()
