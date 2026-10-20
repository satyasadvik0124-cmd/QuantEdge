"""
QuantEdge: leakage-aware expanding walk-forward ML confidence evaluation.

Run from the QuantEdge project root:
    python .\analysis\walk_forward_ml_confidence_by_pair.py

Reads the 5Y candles, SMC signals, and existing Entry-Touch outcome comparison files.
Trains a fresh Random Forest separately for GBPUSD and XAUUSD using only earlier trades
whose Entry-Touch outcome was already resolved before each signal time.

Writes NEW files only under:
    outputs/ml/walk_forward_evaluation/

It does not modify strategy rules, signals, entries, SL/TP, RR, saved models, or backtests.

Important:
- Technical features use only candles whose close time is <= signal_time.
- Training labels are eligible only when entry_touch_exit_time < signal_time.
- Outcome rows are matched using signal_time, direction, entry, SL, and TP (not row order).
- Entry-Touch results retain the project's existing assumption: do not check SL/TP on the
  candle that first touches entry; start exit checks on the following candle.
- Random Forest scores are raw model scores, not calibrated probabilities.
- Drawdown is a signal-order diagnostic, not a portfolio simulation of overlapping trades.
"""

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "ml" / "walk_forward_evaluation"
BAR_MINUTES = 15
MIN_HISTORY = 60
MIN_TRAINING_TRADES = 100
RANDOM_STATE = 42

PAIRS = {
    "GBPUSD": {
        "candles": ROOT / "data" / "GBPUSD_M15_5Y.csv",
        "signals": ROOT / "outputs" / "multi_pair_5y" / "GBPUSD" / "full_available" / "outputs" / "signals_v3.csv",
        "comparison": ROOT / "outputs" / "ml" / "gbpusd_same_signals_method_comparison.csv",
    },
    "XAUUSD": {
        "candles": ROOT / "data" / "XAUUSD_M15_5Y.csv",
        "signals": ROOT / "outputs" / "multi_pair_5y" / "XAUUSD" / "full_available" / "outputs" / "signals_v3.csv",
        "comparison": ROOT / "outputs" / "ml" / "xauusd_same_signals_method_comparison.csv",
    },
}

FEATURES = [
    "rsi_14", "macd_atr", "macd_hist_atr", "ema9_vs_ema21_atr",
    "ema21_vs_ema50_atr", "close_vs_ema9_atr", "atr_14", "adx_14",
    "bb_position", "return_1", "return_4", "return_16",
    "candle_body_ratio", "candle_direction", "direction_buy",
    "risk_distance", "risk_distance_atr",
]
BANDS = ["<40%", "40–<50%", "50–<60%", "≥60%"]


def find_col(df, names, label):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    raise ValueError(f"Missing {label} column. Available columns: {df.columns.tolist()}")


def calc_rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - 100 / (1 + rs)
    result = result.mask((avg_loss == 0) & (avg_gain > 0), 100)
    return result.mask((avg_gain == 0) & (avg_loss > 0), 0)


def build_features(candles):
    c = candles.copy()
    c["ema_9"] = c.close.ewm(span=9, adjust=False).mean()
    c["ema_21"] = c.close.ewm(span=21, adjust=False).mean()
    c["ema_50"] = c.close.ewm(span=50, adjust=False).mean()
    c["rsi_14"] = calc_rsi(c.close)

    ema12 = c.close.ewm(span=12, adjust=False).mean()
    ema26 = c.close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    c["macd"] = macd
    c["macd_hist"] = macd - macd_signal

    previous_close = c.close.shift(1)
    true_range = pd.concat(
        [c.high - c.low, (c.high - previous_close).abs(), (c.low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    c["atr_14"] = true_range.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    up_move = c.high.diff()
    down_move = -c.low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=c.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=c.index)
    atr = c.atr_14.replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    c["adx_14"] = dx.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    mid = c.close.rolling(20).mean()
    sd = c.close.rolling(20).std()
    upper, lower = mid + 2 * sd, mid - 2 * sd
    c["bb_position"] = (c.close - lower) / (upper - lower).replace(0, np.nan)

    for n in (1, 4, 16):
        c[f"return_{n}"] = c.close.pct_change(n)

    candle_range = (c.high - c.low).replace(0, np.nan)
    c["candle_body_ratio"] = (c.close - c.open).abs() / candle_range
    c["candle_direction"] = np.sign(c.close - c.open)
    c["close_vs_ema9_atr"] = (c.close - c.ema_9) / atr
    c["ema9_vs_ema21_atr"] = (c.ema_9 - c.ema_21) / atr
    c["ema21_vs_ema50_atr"] = (c.ema_21 - c.ema_50) / atr
    c["macd_atr"] = c.macd / atr
    c["macd_hist_atr"] = c.macd_hist / atr
    return c


def load_candles(path):
    raw = pd.read_csv(path)
    col_map = {
        "time": find_col(raw, ["time", "datetime", "date", "timestamp"], "candle time"),
        "open": find_col(raw, ["open", "o"], "open"),
        "high": find_col(raw, ["high", "h"], "high"),
        "low": find_col(raw, ["low", "l"], "low"),
        "close": find_col(raw, ["close", "c"], "close"),
    }
    c = pd.DataFrame({key: raw[value] for key, value in col_map.items()})
    c["time"] = pd.to_datetime(c.time, errors="coerce")
    for col in ["open", "high", "low", "close"]:
        c[col] = pd.to_numeric(c[col], errors="coerce")
    c = c.dropna().sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    return build_features(c)


def normalize_signals(signals):
    s = signals.copy().reset_index(drop=True)
    required = ["signal_time", "direction", "entry", "sl", "tp"]
    missing = [c for c in required if c not in s.columns]
    if missing:
        raise ValueError(f"Signals CSV missing required columns: {missing}")
    s["signal_time"] = pd.to_datetime(s["signal_time"], errors="coerce")
    s["direction"] = s.direction.astype(str).str.upper().str.strip()
    for col in ["entry", "sl", "tp"]:
        s[col] = pd.to_numeric(s[col], errors="coerce")
    s["signal_row_id"] = np.arange(len(s), dtype=int)
    return s


def add_match_keys(df):
    out = df.copy()
    out["signal_time"] = pd.to_datetime(out["signal_time"], errors="coerce")
    out["direction"] = out["direction"].astype(str).str.upper().str.strip()
    for col in ["entry", "sl", "tp"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    # Rounding absorbs CSV float formatting differences while retaining price precision.
    out["__match_key"] = (
        out["signal_time"].dt.strftime("%Y-%m-%d %H:%M:%S.%f").fillna("NaT")
        + "|" + out["direction"].fillna("")
        + "|" + out["entry"].round(8).map(lambda x: "nan" if pd.isna(x) else f"{x:.8f}")
        + "|" + out["sl"].round(8).map(lambda x: "nan" if pd.isna(x) else f"{x:.8f}")
        + "|" + out["tp"].round(8).map(lambda x: "nan" if pd.isna(x) else f"{x:.8f}")
    )
    return out


def attach_outcomes(signals, comparison, pair):
    # Match by actual signal attributes rather than assuming the two CSVs share row order.
    comp = comparison.copy()
    aliases = {
        "signal_time": ["signal_time"],
        "direction": ["direction"],
        "entry": ["entry"],
        "sl": ["sl"],
        "tp": ["tp"],
    }
    for canonical, options in aliases.items():
        actual = next((x for x in options if x in comp.columns), None)
        if actual is None:
            raise ValueError(f"{pair}: comparison file lacks matching column {canonical!r}.")
        if actual != canonical:
            comp = comp.rename(columns={actual: canonical})

    outcome_col = "entry_touch_result"
    if outcome_col not in comp.columns:
        raise ValueError(f"{pair}: comparison file lacks {outcome_col!r}.")
    if "entry_touch_exit_time" not in comp.columns:
        raise ValueError(f"{pair}: comparison file lacks 'entry_touch_exit_time'.")

    sig_keys = add_match_keys(signals)
    comp_keys = add_match_keys(comp)
    duplicates = int(comp_keys["__match_key"].duplicated(keep=False).sum())
    if duplicates:
        raise ValueError(
            f"{pair}: {duplicates} comparison rows have duplicate composite keys; "
            "stopping rather than risk joining the wrong outcomes."
        )

    outcome_cols = [
        "__match_key", outcome_col, "entry_touch_time", "entry_touch_exit_time",
        "entry_touch_exit_reason",
    ]
    for optional in ["original_result", "rr"]:
        if optional in comp_keys.columns:
            outcome_cols.append(optional)
    merged = sig_keys.merge(
        comp_keys[outcome_cols].drop_duplicates("__match_key"),
        on="__match_key", how="left", validate="many_to_one", indicator=True,
    )
    merged["outcome_match_status"] = np.where(merged["_merge"].eq("both"), "MATCHED", "NO_OUTCOME_MATCH")
    merged = merged.drop(columns=["_merge", "__match_key"])
    merged["entry_touch_result"] = merged["entry_touch_result"].astype(str).str.upper().str.strip()
    merged["entry_touch_exit_time"] = pd.to_datetime(merged["entry_touch_exit_time"], errors="coerce")
    merged["entry_touch_R"] = np.select(
        [merged.entry_touch_result.eq("WIN"), merged.entry_touch_result.eq("LOSS")],
        [4.0, -1.0], default=np.nan
    )
    return merged


def make_model():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=300,
            max_depth=4,
            min_samples_leaf=8,
            max_features="sqrt",
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])


def build_signal_features(signals, candles, pair):
    records = []
    candle_times = candles["time"]
    candle_close_times = candle_times + pd.Timedelta(minutes=BAR_MINUTES)

    for _, signal in signals.iterrows():
        record = {"signal_row_id": int(signal.signal_row_id), "ml_feature_status": "OK"}
        t = signal.signal_time
        direction = signal.direction
        if pd.isna(t):
            record["ml_feature_status"] = "INVALID_SIGNAL_TIME"
            records.append(record)
            continue
        if direction not in ("BUY", "SELL"):
            record["ml_feature_status"] = "INVALID_DIRECTION"
            records.append(record)
            continue

        eligible_idx = np.flatnonzero((candle_close_times <= t).to_numpy())
        if len(eligible_idx) < MIN_HISTORY:
            record["ml_feature_status"] = "INSUFFICIENT_COMPLETED_CANDLE_HISTORY"
            records.append(record)
            continue

        candle = candles.iloc[int(eligible_idx[-1])]
        record["ml_feature_candle_time"] = candle.time
        record["ml_feature_candle_close_time"] = candle_close_times.iloc[int(eligible_idx[-1])]
        if record["ml_feature_candle_close_time"] > t:
            raise RuntimeError(f"{pair}: feature candle is later than signal time.")

        for name in [
            "rsi_14", "macd_atr", "macd_hist_atr", "ema9_vs_ema21_atr",
            "ema21_vs_ema50_atr", "close_vs_ema9_atr", "atr_14", "adx_14",
            "bb_position", "return_1", "return_4", "return_16",
            "candle_body_ratio", "candle_direction",
        ]:
            record[name] = candle.get(name, np.nan)

        risk = signal.entry - signal.sl if direction == "BUY" else signal.sl - signal.entry
        record["direction_buy"] = int(direction == "BUY")
        record["risk_distance"] = risk
        record["risk_distance_atr"] = risk / candle.atr_14 if pd.notna(candle.atr_14) and candle.atr_14 != 0 else np.nan
        records.append(record)

    features = pd.DataFrame(records)
    out = signals.merge(features, on="signal_row_id", how="left", validate="one_to_one")
    X = out[FEATURES].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    missing = X.isna().any(axis=1)
    bad_status = out.ml_feature_status.eq("OK") & missing
    out.loc[bad_status, "ml_feature_status"] = "MISSING_OR_NONFINITE_FEATURES"
    return out, X


def confidence_band(score):
    if pd.isna(score):
        return "NOT SCORED"
    if score < 0.40:
        return "<40%"
    if score < 0.50:
        return "40–<50%"
    if score < 0.60:
        return "50–<60%"
    return "≥60%"


def calculate_metrics(group, pair, band):
    resolved = group[group.entry_touch_result.isin(["WIN", "LOSS"])].sort_values(
        ["signal_time", "signal_row_id"]
    )
    r_values = resolved["entry_touch_R"].astype(float)
    wins = int(resolved.entry_touch_result.eq("WIN").sum())
    losses = int(resolved.entry_touch_result.eq("LOSS").sum())
    gross_profit = float(r_values[r_values > 0].sum())
    gross_loss = float(-r_values[r_values < 0].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else (np.inf if gross_profit > 0 else np.nan)
    equity = r_values.cumsum()
    drawdown = float((equity.cummax() - equity).max()) if len(equity) else 0.0

    return {
        "pair": pair,
        "confidence_band": band,
        "signals_scored": int(group["ml_estimated_win_score"].notna().sum()),
        "resolved_trades": int(len(resolved)),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(100 * wins / len(resolved), 2) if len(resolved) else np.nan,
        "net_R": round(float(r_values.sum()), 2),
        "profit_factor": round(pf, 4) if np.isfinite(pf) else ("Infinity" if pf == np.inf else np.nan),
        "max_drawdown_R_trade_sequence": round(drawdown, 2),
        "unresolved_or_unmatched": int(group["entry_touch_result"].isin(["WIN", "LOSS"]).eq(False).sum()),
        "mean_model_score_pct": round(float(group["ml_estimated_win_score"].mean() * 100), 2)
            if group["ml_estimated_win_score"].notna().any() else np.nan,
    }


def evaluate_pair(pair, cfg):
    for key, path in cfg.items():
        if not path.exists():
            raise FileNotFoundError(f"{pair}: required {key} file not found: {path}")

    print(f"\n[{pair}] Loading candles, signals, and Entry-Touch outcomes...")
    candles = load_candles(cfg["candles"])
    signals = normalize_signals(pd.read_csv(cfg["signals"]))
    comparison = pd.read_csv(cfg["comparison"])
    merged = attach_outcomes(signals, comparison, pair)
    merged, _ = build_signal_features(merged, candles, pair)

    # Keep the original signal rows and outcomes, but score only when enough valid past
    # outcomes had fully exited before the current signal timestamp.
    merged = merged.sort_values(["signal_time", "signal_row_id"]).reset_index(drop=True)

    merged["ml_estimated_win_score"] = np.nan
    merged["training_rows_before_prediction"] = 0
    merged["training_last_exit_time"] = pd.NaT
    merged["walk_forward_status"] = "NOT SCORED: insufficient prior resolved trades"
    label_ok = merged["entry_touch_result"].isin(["WIN", "LOSS"]) & merged["entry_touch_exit_time"].notna()

    # Rebuild an explicitly keyed feature matrix in the same sorted order as merged.
    feature_frame = build_feature_frame_from_sorted(merged, candles, pair)
    feature_ok = merged["ml_feature_status"].eq("OK") & feature_frame[FEATURES].notna().all(axis=1)

    last_train_signature = None
    fitted_model = None
    scored = 0
    for i, row in merged.iterrows():
        if not feature_ok.iloc[i] or not np.isfinite(feature_frame.loc[i, FEATURES].to_numpy(dtype=float)).all():
            merged.at[i, "walk_forward_status"] = "NOT SCORED: invalid features"
            continue
        t = row.signal_time
        if pd.isna(t):
            merged.at[i, "walk_forward_status"] = "NOT SCORED: invalid signal time"
            continue

        eligible = (
            label_ok
            & (merged["entry_touch_exit_time"] < t)
            & feature_ok
        )
        train_idx = np.flatnonzero(eligible.to_numpy() & (np.arange(len(merged)) < i))
        if len(train_idx) < MIN_TRAINING_TRADES:
            merged.at[i, "training_rows_before_prediction"] = int(len(train_idx))
            merged.at[i, "walk_forward_status"] = f"NOT SCORED: fewer than {MIN_TRAINING_TRADES} prior resolved trades"
            continue

        y_train = merged.iloc[train_idx]["entry_touch_result"].eq("WIN").astype(int)
        if y_train.nunique() < 2:
            merged.at[i, "walk_forward_status"] = "NOT SCORED: training labels contain one class"
            continue

        signature = tuple(train_idx.tolist())
        if signature != last_train_signature:
            fitted_model = make_model()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fitted_model.fit(feature_frame.iloc[train_idx][FEATURES], y_train)
            last_train_signature = signature

        row_x = feature_frame.iloc[[i]][FEATURES]
        probability = fitted_model.predict_proba(row_x)[0]
        classes = list(fitted_model.named_steps["model"].classes_)
        win_index = classes.index(1)
        score = float(probability[win_index])

        merged.at[i, "ml_estimated_win_score"] = score
        merged.at[i, "training_rows_before_prediction"] = int(len(train_idx))
        merged.at[i, "training_last_exit_time"] = merged.iloc[train_idx]["entry_touch_exit_time"].max()
        merged.at[i, "walk_forward_status"] = "SCORED"
        scored += 1

    merged["confidence_band"] = merged["ml_estimated_win_score"].map(confidence_band)
    merged["ml_estimated_win_score_pct"] = merged["ml_estimated_win_score"] * 100
    merged["ml_score_warning"] = (
        "Raw expanding walk-forward Random Forest score; not calibrated. "
        "Only prior resolved Entry-Touch outcomes used for training."
    )

    scoreable = merged[merged.ml_estimated_win_score.notna()]
    summary_rows = [calculate_metrics(scoreable, pair, "ALL SCORED (baseline)")]
    for band in BANDS:
        summary_rows.append(calculate_metrics(scoreable[scoreable.confidence_band.eq(band)], pair, band))
    summary = pd.DataFrame(summary_rows)

    pred_path = OUT_DIR / f"{pair.lower()}_walk_forward_predictions.csv"
    summary_path = OUT_DIR / f"{pair.lower()}_walk_forward_band_summary.csv"
    merged.to_csv(pred_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"[{pair}] candles={len(candles):,}; signals={len(merged):,}; walk-forward scored={scored:,}")
    print("Outcome match status:\n" + merged["outcome_match_status"].value_counts(dropna=False).to_string())
    print("Walk-forward status:\n" + merged["walk_forward_status"].value_counts(dropna=False).to_string())
    print(summary.to_string(index=False))
    print(f"Saved: {pred_path}\nSaved: {summary_path}")
    return summary, merged


def build_feature_frame_from_sorted(merged, candles, pair):
    """Recreate feature rows keyed by signal_row_id, preserving sorted signal order."""
    # build_signal_features computes every row without labels, so it is safe to call again.
    # Remove outcome columns only by selecting the required signal fields.
    signal_fields = ["signal_row_id", "signal_time", "direction", "entry", "sl", "tp"]
    temp = merged[signal_fields].copy()
    # build_signal_features expects signal_row_id to exist and retains the other columns.
    with_features, X = build_signal_features(temp, candles, pair)
    # Its merge retains the input order; join by ID to guarantee alignment.
    keyed = with_features[["signal_row_id"] + FEATURES].drop_duplicates("signal_row_id")
    keyed = merged[["signal_row_id"]].merge(keyed, on="signal_row_id", how="left", validate="one_to_one")
    return keyed[FEATURES].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_summaries = []
    all_predictions = []

    for pair, cfg in PAIRS.items():
        summary, predictions = evaluate_pair(pair, cfg)
        all_summaries.append(summary)
        all_predictions.append(predictions.assign(pair=pair))

    combined_summary = pd.concat(all_summaries, ignore_index=True)
    combined_path = OUT_DIR / "all_pairs_walk_forward_band_summary.csv"
    combined_summary.to_csv(combined_path, index=False)

    combined_predictions = pd.concat(all_predictions, ignore_index=True)
    combined_predictions_path = OUT_DIR / "all_pairs_walk_forward_predictions.csv"
    combined_predictions.to_csv(combined_predictions_path, index=False)

    report_path = OUT_DIR / "walk_forward_report.txt"
    lines = [
        "QUANTEDGE — LEAKAGE-AWARE WALK-FORWARD ML CONFIDENCE EVALUATION",
        "=" * 72,
        "Each prediction is trained only on prior signals with resolved outcomes whose exit time is strictly before the prediction signal time.",
        f"Minimum prior resolved training trades: {MIN_TRAINING_TRADES}",
        "Feature timing: only candles whose close time is <= signal_time.",
        "Outcome matching: signal_time + direction + entry + SL + TP composite key.",
        "Outcome: existing Entry-Touch result (WIN=+4R, LOSS=-1R).",
        "Entry-Touch method skips SL/TP checks on the entry-touch candle.",
        "Scores are raw model scores, not calibrated probabilities.",
        "Max drawdown is a signal-order diagnostic; it is not a portfolio simulation for overlapping trades.",
        "Do not filter live trades based on this exploratory evaluation alone.",
        "",
        "Summary by pair and confidence band:",
        combined_summary.to_string(index=False),
        "",
        f"Combined predictions: {combined_predictions_path}",
        f"Combined summary: {combined_path}",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
