"""
Compare the original QuantEdge V1 backtest outcomes with a diagnostic
alternative that requires a limit-entry price touch before checking exits.

IMPORTANT:
- This script does NOT modify backtest_v1.py or any original CSV.
- It does NOT regenerate signals.
- It assumes BUY entries are limit orders filled when candle low <= entry,
  and SELL entries are limit orders filled when candle high >= entry.
- To avoid guessing intrabar order, SL/TP checking starts on the candle
  AFTER the entry-touch candle.
- This is a comparison scenario, not automatically the correct execution model.
"""

from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import HISTORICAL_FILE

SIGNALS_FILE = ROOT / "outputs" / "signals_v3.csv"
ORIGINAL_RESULTS_FILE = ROOT / "outputs" / "backtest_results_v1.csv"
OUTPUT_DIR = ROOT / "outputs" / "ml"
COMPARISON_FILE = OUTPUT_DIR / "backtest_v1_vs_entry_touch_comparison.csv"
SUMMARY_FILE = OUTPUT_DIR / "backtest_v1_vs_entry_touch_summary.txt"


def load_csv(path, label):
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        raise ValueError(f"{label} is empty: {path}")
    if frame.empty:
        raise ValueError(f"{label} has no rows: {path}")
    return frame


def outcome_after_entry_touch(candles, start_idx, direction, entry_price, sl, tp):
    """
    Alternative limit-order scenario:
    1. Search after the signal candle for entry touch.
    2. Start SL/TP checks from the following candle.
    3. If SL and TP are both hit in the same exit-check candle, record LOSS
       (same conservative assumption as the original backtester).
    """
    entry_idx = None

    for i in range(start_idx + 1, len(candles)):
        candle = candles.iloc[i]
        if direction == "BUY" and candle["low"] <= entry_price:
            entry_idx = i
            break
        if direction == "SELL" and candle["high"] >= entry_price:
            entry_idx = i
            break

    if entry_idx is None:
        return "NO_ENTRY", None, None

    for i in range(entry_idx + 1, len(candles)):
        candle = candles.iloc[i]

        if direction == "BUY":
            sl_hit = candle["low"] <= sl
            tp_hit = candle["high"] >= tp
        elif direction == "SELL":
            sl_hit = candle["high"] >= sl
            tp_hit = candle["low"] <= tp
        else:
            return "INVALID_DIRECTION", entry_idx, None

        if sl_hit:
            return "LOSS", entry_idx, i
        if tp_hit:
            return "WIN", entry_idx, i

    return "OPEN", entry_idx, None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    candles = load_csv(Path(HISTORICAL_FILE), "Historical candle file")
    signals = load_csv(SIGNALS_FILE, "Signals file")
    original = load_csv(ORIGINAL_RESULTS_FILE, "Original backtest results")

    required_candle_cols = {"time", "high", "low"}
    required_signal_cols = {"signal_time", "direction", "entry", "sl", "tp"}
    required_result_cols = {"signal_time", "direction", "entry", "sl", "tp", "result"}

    for label, frame, required in [
        ("Historical candles", candles, required_candle_cols),
        ("Signals", signals, required_signal_cols),
        ("Original results", original, required_result_cols),
    ]:
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{label} missing required columns: {sorted(missing)}")

    candles["time"] = pd.to_datetime(candles["time"], errors="coerce")
    signals["signal_time"] = pd.to_datetime(signals["signal_time"], errors="coerce")
    original["signal_time"] = pd.to_datetime(original["signal_time"], errors="coerce")

    for col in ["high", "low"]:
        candles[col] = pd.to_numeric(candles[col], errors="coerce")
    for col in ["entry", "sl", "tp"]:
        signals[col] = pd.to_numeric(signals[col], errors="coerce")
        original[col] = pd.to_numeric(original[col], errors="coerce")

    candles = candles.dropna(subset=["time", "high", "low"]).sort_values("time").reset_index(drop=True)
    candle_index_by_time = {}
    for idx, t in enumerate(candles["time"]):
        candle_index_by_time.setdefault(t, idx)

    # Build an exact-key lookup so original outcomes are matched to the corresponding signal.
    key_cols = ["signal_time", "direction", "entry", "sl", "tp"]
    original_lookup = {}
    for _, row in original.iterrows():
        key = (
            row["signal_time"], str(row["direction"]).upper(),
            row["entry"], row["sl"], row["tp"]
        )
        original_lookup.setdefault(key, row["result"])

    rows = []
    for _, signal in signals.iterrows():
        signal_time = signal["signal_time"]
        direction = str(signal["direction"]).upper()
        entry_price = signal["entry"]
        sl = signal["sl"]
        tp = signal["tp"]

        key = (signal_time, direction, entry_price, sl, tp)
        original_result = original_lookup.get(key, "NOT_MATCHED")

        row = {
            "signal_time": signal_time,
            "direction": direction,
            "entry": entry_price,
            "sl": sl,
            "tp": tp,
            "original_result": original_result,
            "alternative_result": "NOT_EVALUATED",
            "entry_touch_time": None,
            "exit_check_time": None,
            "comparison": "NOT_MATCHED_TO_ORIGINAL",
            "notes": "",
        }

        if pd.isna(signal_time) or pd.isna(entry_price) or pd.isna(sl) or pd.isna(tp):
            row["alternative_result"] = "INVALID_SIGNAL_DATA"
            row["notes"] = "Missing or invalid signal timestamp/price."
            rows.append(row)
            continue

        if signal_time not in candle_index_by_time:
            row["alternative_result"] = "SIGNAL_CANDLE_NOT_FOUND"
            row["notes"] = "No exact candle timestamp match; not evaluated."
            rows.append(row)
            continue

        start_idx = candle_index_by_time[signal_time]
        alt_result, entry_idx, exit_idx = outcome_after_entry_touch(
            candles, start_idx, direction, entry_price, sl, tp
        )

        row["alternative_result"] = alt_result
        if entry_idx is not None:
            row["entry_touch_time"] = candles.iloc[entry_idx]["time"]
        if exit_idx is not None:
            row["exit_check_time"] = candles.iloc[exit_idx]["time"]

        if original_result == "NOT_MATCHED":
            row["comparison"] = "NOT_MATCHED_TO_ORIGINAL"
        elif alt_result == original_result:
            row["comparison"] = "SAME"
        else:
            row["comparison"] = "CHANGED"

        if alt_result == "NO_ENTRY":
            row["notes"] = "Entry price was not touched after the signal candle."
        elif alt_result == "OPEN":
            row["notes"] = "Entry touched, but no SL/TP was reached afterward in available data."
        elif alt_result == "SIGNAL_CANDLE_NOT_FOUND":
            row["notes"] = "Signal timestamp did not exactly match a candle timestamp."

        rows.append(row)

    comparison = pd.DataFrame(rows)
    comparison.to_csv(COMPARISON_FILE, index=False)

    matched = comparison[comparison["original_result"] != "NOT_MATCHED"]
    changed = int((matched["comparison"] == "CHANGED").sum())
    same = int((matched["comparison"] == "SAME").sum())
    no_entry = int((comparison["alternative_result"] == "NO_ENTRY").sum())
    alt_wins = int((comparison["alternative_result"] == "WIN").sum())
    alt_losses = int((comparison["alternative_result"] == "LOSS").sum())
    alt_open = int((comparison["alternative_result"] == "OPEN").sum())
    original_wins = int((matched["original_result"] == "WIN").sum())
    original_losses = int((matched["original_result"] == "LOSS").sum())

    resolved_alt = alt_wins + alt_losses
    alt_win_rate = (alt_wins / resolved_alt * 100) if resolved_alt else 0.0
    resolved_original = original_wins + original_losses
    original_win_rate = (original_wins / resolved_original * 100) if resolved_original else 0.0

    summary_lines = [
        "QuantEdge V1 vs Entry-Touch Scenario Comparison",
        "=" * 48,
        "",
        "This is a diagnostic comparison, not proof that the alternative is the correct execution model.",
        "Alternative assumption: BUY limit entry fills when low <= entry; SELL limit entry fills when high >= entry.",
        "SL/TP checks begin on the candle AFTER entry-touch candle to avoid assuming intrabar order.",
        "Both SL and TP on the same exit-check candle are treated as LOSS.",
        "",
        f"Signals loaded: {len(signals)}",
        f"Original result rows matched: {len(matched)}",
        f"Same outcome: {same}",
        f"Changed outcome/status: {changed}",
        f"Not matched to original result: {len(comparison) - len(matched)}",
        "",
        "Original matched outcomes:",
        f"  Wins: {original_wins}",
        f"  Losses: {original_losses}",
        f"  Resolved-trade win rate: {original_win_rate:.2f}%",
        "",
        "Alternative entry-touch scenario:",
        f"  Wins: {alt_wins}",
        f"  Losses: {alt_losses}",
        f"  Open after entry: {alt_open}",
        f"  Entry never touched: {no_entry}",
        f"  Resolved-trade win rate: {alt_win_rate:.2f}%",
        "",
        f"Detailed comparison CSV: {COMPARISON_FILE}",
    ]
    SUMMARY_FILE.write_text("\n".join(summary_lines), encoding="utf-8")

    print("\n".join(summary_lines))
    print(f"\nSaved comparison: {COMPARISON_FILE}")
    print(f"Saved summary:    {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
