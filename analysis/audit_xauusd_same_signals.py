from pathlib import Path
import pandas as pd

# Finds project root whether this file is placed in the root or analysis/.
HERE = Path(__file__).resolve().parent
ROOT = HERE if (HERE / "data").is_dir() else HERE.parent

DATA_FILE = ROOT / "data" / "XAUUSD_M15_5Y.csv"
ISOLATED_SIGNALS = ROOT / "outputs" / "multi_pair_5y" / "XAUUSD" / "full_available" / "outputs" / "signals_v3.csv"
SHARED_SIGNALS = ROOT / "outputs" / "signals_v3.csv"
OUT_DIR = ROOT / "outputs" / "ml"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return pd.read_csv(path)

def classify_original(candles, start_idx, direction, sl, tp):
    # Mirrors backtest_v1.py: begin after the signal candle; SL checked before TP.
    for i in range(start_idx + 1, len(candles)):
        c = candles.iloc[i]
        if direction == "BUY":
            if c["low"] <= sl:
                return "LOSS", candles.iloc[i]["time"], "SL"
            if c["high"] >= tp:
                return "WIN", candles.iloc[i]["time"], "TP"
        elif direction == "SELL":
            if c["high"] >= sl:
                return "LOSS", candles.iloc[i]["time"], "SL"
            if c["low"] <= tp:
                return "WIN", candles.iloc[i]["time"], "TP"
    return "OPEN", None, "NO_EXIT"

def classify_entry_touch(candles, start_idx, direction, entry, sl, tp):
    # Entry must be touched after the signal candle. Once touched, exit checking
    # begins on the next candle, matching the previous diagnostic's assumption.
    entry_idx = None
    for i in range(start_idx + 1, len(candles)):
        c = candles.iloc[i]
        if c["low"] <= entry <= c["high"]:
            entry_idx = i
            break
    if entry_idx is None:
        return "NO_ENTRY", None, None, "ENTRY_NEVER_TOUCHED"
    for i in range(entry_idx + 1, len(candles)):
        c = candles.iloc[i]
        if direction == "BUY":
            if c["low"] <= sl:
                return "LOSS", candles.iloc[entry_idx]["time"], candles.iloc[i]["time"], "SL"
            if c["high"] >= tp:
                return "WIN", candles.iloc[entry_idx]["time"], candles.iloc[i]["time"], "TP"
        elif direction == "SELL":
            if c["high"] >= sl:
                return "LOSS", candles.iloc[entry_idx]["time"], candles.iloc[i]["time"], "SL"
            if c["low"] <= tp:
                return "WIN", candles.iloc[entry_idx]["time"], candles.iloc[i]["time"], "TP"
    return "OPEN", candles.iloc[entry_idx]["time"], None, "NO_EXIT_AFTER_ENTRY"

def outcome_summary(df, result_col, rr_col="rr"):
    labels = df[result_col].astype(str).str.upper()
    wins = int((labels == "WIN").sum())
    losses = int((labels == "LOSS").sum())
    opened = int((labels == "OPEN").sum())
    no_entry = int((labels == "NO_ENTRY").sum())
    resolved = wins + losses
    win_rate = 100 * wins / resolved if resolved else 0.0

    rrs = pd.to_numeric(df[rr_col], errors="coerce") if rr_col in df.columns else pd.Series([4.0] * len(df))
    rs = []
    for i, label in enumerate(labels):
        if label == "WIN":
            rr = rrs.iloc[i] if i < len(rrs) and pd.notna(rrs.iloc[i]) else 4.0
            rs.append(float(rr))
        elif label == "LOSS":
            rs.append(-1.0)
        else:
            rs.append(0.0)
    gross_profit = sum(x for x in rs if x > 0)
    gross_loss = -sum(x for x in rs if x < 0)
    pf = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
    equity = pd.Series(rs, dtype=float).cumsum()
    max_dd = float((equity.cummax() - equity).max()) if len(equity) else 0.0
    return {
        "method": result_col,
        "total_signals": len(df),
        "wins": wins,
        "losses": losses,
        "open_after_entry": opened,
        "entry_never_touched": no_entry,
        "resolved_trades": resolved,
        "win_rate_pct": round(win_rate, 2),
        "net_R_excluding_unresolved": round(sum(rs), 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else "Infinity",
        "max_drawdown_R_trade_sequence": round(max_dd, 2),
    }

def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")
    signal_path = ISOLATED_SIGNALS if ISOLATED_SIGNALS.exists() else SHARED_SIGNALS
    candles = load_csv(DATA_FILE)
    signals = load_csv(signal_path)

    required_candles = {"time", "open", "high", "low", "close"}
    required_signals = {"signal_time", "direction", "entry", "sl", "tp"}
    if not required_candles.issubset(candles.columns):
        raise ValueError(f"Candle CSV missing columns: {sorted(required_candles-set(candles.columns))}")
    if not required_signals.issubset(signals.columns):
        raise ValueError(f"Signal CSV missing columns: {sorted(required_signals-set(signals.columns))}")

    candles["time"] = pd.to_datetime(candles["time"], errors="raise")
    signals["signal_time"] = pd.to_datetime(signals["signal_time"], errors="raise")
    candles = candles.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    signals = signals.copy()
    if "rr" not in signals.columns:
        signals["rr"] = 4.0

    time_to_index = {t: i for i, t in enumerate(candles["time"])}
    rows = []
    for signal_id, s in signals.reset_index(drop=True).iterrows():
        t = s["signal_time"]
        direction = str(s["direction"]).upper()
        entry, sl, tp = float(s["entry"]), float(s["sl"]), float(s["tp"])
        base = {
            "signal_id": signal_id,
            "signal_time": t,
            "direction": direction,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": float(s["rr"]) if pd.notna(s["rr"]) else 4.0,
        }
        idx = time_to_index.get(t)
        if idx is None:
            rows.append({
                **base,
                "original_result": "NO_SIGNAL_CANDLE",
                "original_exit_time": None,
                "original_exit_reason": "TIMESTAMP_NOT_FOUND",
                "entry_touch_result": "NO_SIGNAL_CANDLE",
                "entry_touch_time": None,
                "entry_touch_exit_time": None,
                "entry_touch_exit_reason": "TIMESTAMP_NOT_FOUND",
            })
            continue

        orig, orig_exit, orig_reason = classify_original(candles, idx, direction, sl, tp)
        ent_result, ent_time, ent_exit, ent_reason = classify_entry_touch(
            candles, idx, direction, entry, sl, tp
        )
        rows.append({
            **base,
            "original_result": orig,
            "original_exit_time": orig_exit,
            "original_exit_reason": orig_reason,
            "entry_touch_result": ent_result,
            "entry_touch_time": ent_time,
            "entry_touch_exit_time": ent_exit,
            "entry_touch_exit_reason": ent_reason,
        })

    detail = pd.DataFrame(rows)
    detail["outcome_changed"] = detail["original_result"] != detail["entry_touch_result"]
    detail["original_vs_entry_touch"] = detail["original_result"].astype(str) + " -> " + detail["entry_touch_result"].astype(str)

    detail_path = OUT_DIR / "xauusd_same_signals_method_comparison.csv"
    detail.to_csv(detail_path, index=False)

    summaries = pd.DataFrame([
        outcome_summary(detail, "original_result"),
        outcome_summary(detail, "entry_touch_result"),
    ])
    summary_path = OUT_DIR / "xauusd_same_signals_method_summary.csv"
    summaries.to_csv(summary_path, index=False)

    changed = (
        detail[detail["outcome_changed"]]
        .groupby("original_vs_entry_touch", dropna=False)
        .size()
        .rename("count")
        .reset_index()
        .sort_values("count", ascending=False)
    )
    changed_path = OUT_DIR / "xauusd_outcome_changes.csv"
    changed.to_csv(changed_path, index=False)

    print("\n=== INPUTS ===")
    print(f"Candles: {DATA_FILE}")
    print(f"Signals: {signal_path}")
    print(f"Signal count: {len(signals)}")
    print(f"Candle range: {candles['time'].min()} -> {candles['time'].max()}")
    print("\n=== SAME-SIGNAL METHOD COMPARISON ===")
    print(summaries.to_string(index=False))
    print("\n=== OUTCOME TRANSITIONS ===")
    print(changed.to_string(index=False) if not changed.empty else "No outcome differences.")
    print("\n=== OUTPUT FILES ===")
    print(detail_path)
    print(summary_path)
    print(changed_path)
    print("\nInterpretation note: the entry-touch method skips SL/TP checks on the entry candle.")
    print("That assumption can materially affect results; this is a diagnostic, not a final validation.")

if __name__ == "__main__":
    main()
