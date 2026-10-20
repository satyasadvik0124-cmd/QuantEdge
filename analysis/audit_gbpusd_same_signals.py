from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE if (HERE / "data").is_dir() else HERE.parent

DATA_FILE = ROOT / "data" / "GBPUSD_M15_5Y.csv"
SIGNAL_CANDIDATES = [
    ROOT / "outputs" / "multi_pair_5y" / "GBPUSD" / "full_available" / "outputs" / "signals_v3.csv",
    ROOT / "outputs" / "signals_v3.csv",
]
OUT_DIR = ROOT / "outputs" / "ml"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return pd.read_csv(path)

def original_outcome(candles, signal_idx, direction, sl, tp):
    # Mirrors original backtest_v1.py: start after signal candle, SL checked first.
    for i in range(signal_idx + 1, len(candles)):
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

def entry_touch_outcome(candles, signal_idx, direction, entry, sl, tp):
    # Recreates prior diagnostic assumption: entry touch after signal,
    # then begins SL/TP checks from the following candle.
    entry_idx = None
    for i in range(signal_idx + 1, len(candles)):
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

def summarize(df, col):
    labels = df[col].astype(str).str.upper()
    wins = int((labels == "WIN").sum())
    losses = int((labels == "LOSS").sum())
    opens = int((labels == "OPEN").sum())
    no_entry = int((labels == "NO_ENTRY").sum())
    resolved = wins + losses
    win_rate = wins / resolved * 100 if resolved else 0.0
    rr = pd.to_numeric(df["rr"], errors="coerce") if "rr" in df else pd.Series([4.0] * len(df))
    trade_r = []
    for i, label in enumerate(labels):
        if label == "WIN":
            val = rr.iloc[i] if i < len(rr) and pd.notna(rr.iloc[i]) else 4.0
            trade_r.append(float(val))
        elif label == "LOSS":
            trade_r.append(-1.0)
        else:
            trade_r.append(0.0)
    gp = sum(v for v in trade_r if v > 0)
    gl = -sum(v for v in trade_r if v < 0)
    pf = gp / gl if gl else (float("inf") if gp else 0.0)
    eq = pd.Series(trade_r, dtype=float).cumsum()
    dd = float((eq.cummax() - eq).max()) if len(eq) else 0.0
    return {
        "method": col, "signals": len(df), "wins": wins, "losses": losses,
        "open_after_entry": opens, "entry_never_touched": no_entry,
        "resolved_trades": resolved, "win_rate_pct": round(win_rate, 2),
        "net_R_excluding_unresolved": round(sum(trade_r), 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else "Infinity",
        "max_drawdown_R_trade_sequence": round(dd, 2),
    }

def main():
    candles = load_csv(DATA_FILE)
    signals_path = next((p for p in SIGNAL_CANDIDATES if p.exists()), None)
    if signals_path is None:
        raise FileNotFoundError(
            "GBPUSD signals file not found. Expected the isolated signals at "
            f"{SIGNAL_CANDIDATES[0]} or shared signals at {SIGNAL_CANDIDATES[1]}"
        )
    signals = load_csv(signals_path)
    required_candles = {"time", "high", "low"}
    required_signals = {"signal_time", "direction", "entry", "sl", "tp"}
    if not required_candles.issubset(candles.columns):
        raise ValueError(f"Candles missing columns: {sorted(required_candles-set(candles.columns))}")
    if not required_signals.issubset(signals.columns):
        raise ValueError(f"Signals missing columns: {sorted(required_signals-set(signals.columns))}")
    candles["time"] = pd.to_datetime(candles["time"], errors="raise")
    signals["signal_time"] = pd.to_datetime(signals["signal_time"], errors="raise")
    candles = candles.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    signals = signals.copy()
    if "rr" not in signals:
        signals["rr"] = 4.0
    index_map = {t: i for i, t in enumerate(candles["time"])}
    rows = []
    for sid, s in signals.reset_index(drop=True).iterrows():
        base = {
            "signal_id": sid, "signal_time": s["signal_time"],
            "direction": str(s["direction"]).upper(), "entry": float(s["entry"]),
            "sl": float(s["sl"]), "tp": float(s["tp"]),
            "rr": float(s["rr"]) if pd.notna(s["rr"]) else 4.0,
        }
        idx = index_map.get(s["signal_time"])
        if idx is None:
            rows.append({**base, "original_result": "NO_SIGNAL_CANDLE",
                         "original_exit_time": None, "original_exit_reason": "TIMESTAMP_NOT_FOUND",
                         "entry_touch_result": "NO_SIGNAL_CANDLE", "entry_touch_time": None,
                         "entry_touch_exit_time": None, "entry_touch_exit_reason": "TIMESTAMP_NOT_FOUND"})
            continue
        o, ot, oreason = original_outcome(candles, idx, base["direction"], base["sl"], base["tp"])
        e, et, eet, ereason = entry_touch_outcome(
            candles, idx, base["direction"], base["entry"], base["sl"], base["tp"]
        )
        rows.append({**base, "original_result": o, "original_exit_time": ot,
                     "original_exit_reason": oreason, "entry_touch_result": e,
                     "entry_touch_time": et, "entry_touch_exit_time": eet,
                     "entry_touch_exit_reason": ereason})
    detail = pd.DataFrame(rows)
    detail["outcome_changed"] = detail["original_result"] != detail["entry_touch_result"]
    detail["outcome_transition"] = detail["original_result"].astype(str) + " -> " + detail["entry_touch_result"].astype(str)
    summary = pd.DataFrame([summarize(detail, "original_result"), summarize(detail, "entry_touch_result")])
    transitions = detail[detail["outcome_changed"]].groupby("outcome_transition").size().rename("count").reset_index().sort_values("count", ascending=False)

    detail_path = OUT_DIR / "gbpusd_same_signals_method_comparison.csv"
    summary_path = OUT_DIR / "gbpusd_same_signals_method_summary.csv"
    transition_path = OUT_DIR / "gbpusd_outcome_changes.csv"
    detail.to_csv(detail_path, index=False)
    summary.to_csv(summary_path, index=False)
    transitions.to_csv(transition_path, index=False)

    print("\n=== INPUTS ===")
    print(f"Dataset: {DATA_FILE}")
    print(f"Signals: {signals_path}")
    print(f"Signal count: {len(signals)}")
    print(f"Candle range: {candles['time'].min()} -> {candles['time'].max()}")
    print("\n=== SAME-SIGNAL METHOD COMPARISON ===")
    print(summary.to_string(index=False))
    print("\n=== OUTCOME TRANSITIONS ===")
    print(transitions.to_string(index=False) if not transitions.empty else "No outcome differences.")
    print("\n=== OUTPUT FILES ===")
    print(detail_path)
    print(summary_path)
    print(transition_path)
    print("\nCaution: entry-touch method skips SL/TP checks on the entry-touch candle.")
    print("Treat this as a diagnostic, not validated performance.")

if __name__ == "__main__":
    main()
