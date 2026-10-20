"""
QuantEdge timing-aware backtest for corrected SMC entry candidates.

Run from project root:
    python analysis/backtest_v4_timing.py

Inputs:
    outputs/signals_v4_candidates.csv
    data/<PAIR>_<TIMEFRAME>_2Y.csv (resolved through config.py)

Outputs:
    outputs/backtest_results_v4_timing.csv
    outputs/backtest_summary_v4_timing.txt

Execution assumptions:
- Entry is considered eligible at the first M15 candle whose range reaches the
  original OB entry level at/after signal_available_time.
- This is an OHLC range-touch approximation, not tick-accurate fill simulation.
- The entry candle is included when checking SL/TP because the entry and exits
  may all occur within that candle. If both SL and TP are reached in one candle,
  SL is counted first (conservative assumption).
- Trades still open at the end of the dataset are labelled OPEN and excluded
  from win-rate and realized-R calculations.
- Each signal is evaluated independently; overlapping positions are not netted.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import PAIR, TIMEFRAME_NAME, HISTORICAL_FILE  # noqa: E402

OUTPUT_DIR = ROOT / "outputs"
CANDIDATES_FILE = OUTPUT_DIR / "signals_v4_candidates.csv"
RESULTS_FILE = OUTPUT_DIR / "backtest_results_v4_timing.csv"
SUMMARY_FILE = OUTPUT_DIR / "backtest_summary_v4_timing.txt"


def load_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    frame = pd.read_csv(path)
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{path.name} missing required columns {sorted(missing)}. "
            f"Available columns: {list(frame.columns)}"
        )
    return frame


def main() -> None:
    print("\n===== TIMING-AWARE BACKTEST V4 =====")
    print(f"Asset: {PAIR}_{TIMEFRAME_NAME}")
    print(f"Data:  {HISTORICAL_FILE}")

    signals = load_csv(
        CANDIDATES_FILE,
        {
            "source_signal_id", "direction", "signal_available_time",
            "entry_time", "entry", "sl", "tp"
        },
    )
    data = load_csv(
        Path(HISTORICAL_FILE),
        {"time", "open", "high", "low", "close"},
    )

    for col in ["signal_available_time", "entry_time"]:
        signals[col] = pd.to_datetime(signals[col], errors="coerce")
    data["time"] = pd.to_datetime(data["time"], errors="coerce")

    signals = signals.dropna(
        subset=["signal_available_time", "entry_time"]
    ).sort_values(["entry_time", "source_signal_id"]).reset_index(drop=True)
    data = data.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    if data.empty:
        raise SystemExit("Historical price data is empty.")
    if signals.empty:
        raise SystemExit("No eligible candidates found. Run the timing corrector first.")

    data = data.drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)
    time_to_idx = {pd.Timestamp(t): i for i, t in enumerate(data["time"])}

    results = []

    for _, signal in signals.iterrows():
        direction = str(signal["direction"]).upper()
        available_time = pd.Timestamp(signal["signal_available_time"])
        entry_time = pd.Timestamp(signal["entry_time"])
        entry = float(signal["entry"])
        sl = float(signal["sl"])
        tp = float(signal["tp"])

        result = "INVALID"
        exit_time = pd.NaT
        exit_price = None
        bars_held = 0
        note = ""

        if direction not in {"BUY", "SELL"}:
            note = "Unknown direction"
        elif entry_time < available_time:
            note = "Entry timestamp precedes signal availability"
        elif entry_time not in time_to_idx:
            note = "Entry candle timestamp not present in historical data"
        elif direction == "BUY" and not (sl < entry < tp):
            note = "Invalid BUY price ordering"
        elif direction == "SELL" and not (tp < entry < sl):
            note = "Invalid SELL price ordering"
        else:
            entry_idx = time_to_idx[entry_time]
            entry_candle = data.iloc[entry_idx]

            # Verify that the selected candle's range really reaches the entry.
            if direction == "BUY":
                entry_touched = float(entry_candle["low"]) <= entry
            else:
                entry_touched = float(entry_candle["high"]) >= entry

            if not entry_touched:
                note = "Entry level not touched in candidate entry candle"
            else:
                result = "OPEN"
                note = (
                    "OHLC range-touch fill approximation; exact fill and intrabar "
                    "sequence are unknown."
                )

                # Include the entry candle because SL/TP may also be touched
                # after the entry within the same M15 bar.
                for idx in range(entry_idx, len(data)):
                    candle = data.iloc[idx]
                    bars_held += 1
                    high = float(candle["high"])
                    low = float(candle["low"])

                    if direction == "BUY":
                        sl_hit = low <= sl
                        tp_hit = high >= tp
                    else:
                        sl_hit = high >= sl
                        tp_hit = low <= tp

                    # Conservative: if both levels occur in one candle, count SL.
                    if sl_hit:
                        result = "LOSS"
                        exit_time = pd.Timestamp(candle["time"])
                        exit_price = sl
                        if tp_hit:
                            note += " Both SL and TP touched in same candle; SL assumed first."
                        break
                    if tp_hit:
                        result = "WIN"
                        exit_time = pd.Timestamp(candle["time"])
                        exit_price = tp
                        break

                if result == "OPEN":
                    note += " Dataset ended before SL or TP was reached."

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr_target = reward / risk if risk > 0 else None
        realized_r = (
            rr_target if result == "WIN"
            else -1.0 if result == "LOSS"
            else None
        )

        results.append({
            "source_signal_id": signal["source_signal_id"],
            "direction": direction,
            "signal_available_time": available_time,
            "entry_time": entry_time,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "target_rr": rr_target,
            "result": result,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "bars_held": bars_held,
            "realized_r": realized_r,
            "execution_note": note,
        })

    result_df = pd.DataFrame(results)
    result_df.to_csv(RESULTS_FILE, index=False)

    valid = result_df[result_df["result"].isin(["WIN", "LOSS"])]
    wins = int((valid["result"] == "WIN").sum())
    losses = int((valid["result"] == "LOSS").sum())
    open_trades = int((result_df["result"] == "OPEN").sum())
    invalid = int((result_df["result"] == "INVALID").sum())
    total_resolved = len(valid)
    win_rate = (wins / total_resolved * 100) if total_resolved else 0.0
    profit_factor = None
    gross_profit_r = valid.loc[valid["realized_r"] > 0, "realized_r"].sum()
    gross_loss_r = -valid.loc[valid["realized_r"] < 0, "realized_r"].sum()
    if gross_loss_r > 0:
        profit_factor = gross_profit_r / gross_loss_r
    elif gross_profit_r > 0:
        profit_factor = float("inf")
    net_r = valid["realized_r"].sum()
    average_r = valid["realized_r"].mean() if total_resolved else 0.0

    summary_lines = [
        f"Asset: {PAIR}_{TIMEFRAME_NAME}",
        f"Historical file: {HISTORICAL_FILE}",
        f"Candidate signals: {len(signals)}",
        f"Resolved trades (WIN/LOSS): {total_resolved}",
        f"Wins: {wins}",
        f"Losses: {losses}",
        f"Open at end of data: {open_trades}",
        f"Invalid/unprocessed: {invalid}",
        f"Win rate (resolved only): {win_rate:.2f}%",
        f"Gross profit (R): {gross_profit_r:.2f}",
        f"Gross loss (R): {gross_loss_r:.2f}",
        f"Net R (resolved only): {net_r:.2f}",
        f"Average R per resolved trade: {average_r:.3f}",
        f"Profit factor: {profit_factor if profit_factor is not None else 'N/A'}",
        "",
        "Caveats:",
        "- Entry is approximated by M15 candle range touch, not tick-level execution.",
        "- If SL and TP both occur in one candle, SL is assumed first.",
        "- Open trades are excluded from resolved-trade statistics.",
        "- Each signal is evaluated independently; overlapping trades are not netted.",
        "- Results are research estimates, not proof of live execution performance.",
    ]
    SUMMARY_FILE.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("\n===== BACKTEST SUMMARY =====")
    for line in summary_lines[:14]:
        print(line)
    print(f"\nDetailed results: {RESULTS_FILE}")
    print(f"Summary file:     {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
