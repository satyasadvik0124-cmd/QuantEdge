"""
QuantEdge signal-timing correction (separate from the original SMC pipeline).

Run from the QuantEdge project root:
    python analysis/signal_timing_corrector.py

Reads:
    outputs/signals_v3.csv
    outputs/signal_timing_audit.csv
    data/GBPUSD_M15_2Y.csv (through config.py)

Writes:
    outputs/signals_v4_timing_review.csv   - every original signal + timing findings
    outputs/signals_v4_candidates.csv      - candidates with a future entry-level retest

This script does NOT edit the original signal generator, signals_v3.csv, or backtest.
It also does not claim that a candle-range touch proves a precise fill: M15 OHLC
cannot reveal intrabar order or slippage. The next step should use a dedicated
backtester that starts from entry_time and handles ambiguous candles conservatively.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import PAIR, TIMEFRAME_NAME, HISTORICAL_FILE  # noqa: E402

OUT = ROOT / "outputs"
SIGNALS_FILE = OUT / "signals_v3.csv"
AUDIT_FILE = OUT / "signal_timing_audit.csv"
DATA_FILE = Path(HISTORICAL_FILE)

REVIEW_FILE = OUT / "signals_v4_timing_review.csv"
CANDIDATES_FILE = OUT / "signals_v4_candidates.csv"

TIME_COLUMNS_AUDIT = [
    "recorded_signal_time",
    "earliest_valid_available_time",
    "first_entry_touch_after_available",
]
SIGNAL_COLUMNS = ["signal_time", "direction", "entry", "sl", "tp"]


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def main() -> None:
    print("\n===== SIGNAL TIMING CORRECTOR =====")
    print(f"Configured asset: {PAIR}_{TIMEFRAME_NAME}")
    print(f"Historical file:  {DATA_FILE}")

    for path in (SIGNALS_FILE, AUDIT_FILE, DATA_FILE):
        require_file(path)

    signals = pd.read_csv(SIGNALS_FILE)
    audit = pd.read_csv(AUDIT_FILE)
    data = pd.read_csv(DATA_FILE)

    missing_signals = set(SIGNAL_COLUMNS) - set(signals.columns)
    missing_audit = set(TIME_COLUMNS_AUDIT + ["direction", "entry"]) - set(audit.columns)
    missing_data = {"time", "open", "high", "low", "close"} - set(data.columns)

    if missing_signals:
        raise ValueError(f"{SIGNALS_FILE.name} missing columns: {sorted(missing_signals)}")
    if missing_audit:
        raise ValueError(f"{AUDIT_FILE.name} missing columns: {sorted(missing_audit)}")
    if missing_data:
        raise ValueError(f"{DATA_FILE.name} missing columns: {sorted(missing_data)}")

    for col in ["signal_time"]:
        signals[col] = pd.to_datetime(signals[col], errors="coerce")
    for col in TIME_COLUMNS_AUDIT:
        audit[col] = pd.to_datetime(audit[col], errors="coerce")
    data["time"] = pd.to_datetime(data["time"], errors="coerce")

    signals = signals.dropna(subset=["signal_time"]).sort_values("signal_time").reset_index(drop=True)
    audit = audit.sort_values("recorded_signal_time").reset_index(drop=True)
    data = data.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    # Audit's signal_id is created after sorting the same signals by signal_time.
    # Check counts and row identity before relying on row order.
    if len(signals) != len(audit):
        raise ValueError(
            f"Signal count mismatch: signals_v3.csv={len(signals)}, "
            f"signal_timing_audit.csv={len(audit)}. Re-run the timing audit first."
        )

    if not (signals["direction"].astype(str).str.upper().to_numpy()
            == audit["direction"].astype(str).str.upper().to_numpy()).all():
        raise ValueError(
            "Signal ordering/directions do not match between the signal and audit files. "
            "Re-run signal_timing_analyzer.py before this script."
        )

    review_rows = []
    for idx, signal in signals.iterrows():
        audit_row = audit.iloc[idx]
        direction = str(signal["direction"]).upper()
        original_time = pd.Timestamp(signal["signal_time"])
        available_time = audit_row["earliest_valid_available_time"]
        entry_time = audit_row["first_entry_touch_after_available"]
        entry = float(signal["entry"])
        sl = float(signal["sl"])
        tp = float(signal["tp"])

        component_match = bool(audit_row.get("component_match_found", False))
        if pd.isna(available_time):
            status = "UNVERIFIED_COMPONENT_MATCH"
            eligible = False
        elif pd.isna(entry_time):
            status = "NO_FUTURE_ENTRY_LEVEL_RETEST"
            eligible = False
        elif pd.Timestamp(entry_time) < pd.Timestamp(available_time):
            status = "INVALID_ENTRY_TIME_BEFORE_AVAILABILITY"
            eligible = False
        else:
            status = "CANDIDATE_FUTURE_RETEST"
            eligible = True

        # Ensure the future-touch candle actually overlaps the entry level.
        # This verifies a range touch only; it does not prove intrabar fill order.
        if eligible:
            match = data[data["time"] == pd.Timestamp(entry_time)]
            if match.empty:
                status = "ENTRY_TOUCH_TIMESTAMP_NOT_IN_DATA"
                eligible = False
            else:
                candle = match.iloc[0]
                if direction == "BUY":
                    overlap = float(candle["low"]) <= entry
                elif direction == "SELL":
                    overlap = float(candle["high"]) >= entry
                else:
                    overlap = False
                if not overlap:
                    status = "ENTRY_LEVEL_NOT_TOUCHED_IN_MATCHED_CANDLE"
                    eligible = False

        row = {
            "source_signal_id": idx,
            "direction": direction,
            "original_signal_time": original_time,
            "signal_available_time": available_time,
            "entry_time": entry_time,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "risk": abs(entry - sl),
            "reward": abs(tp - entry),
            "rr": (abs(tp - entry) / abs(entry - sl)) if abs(entry - sl) > 0 else None,
            "component_match_found": component_match,
            "entry_touched_before_available": audit_row.get(
                "entry_touched_before_available", pd.NA
            ),
            "minutes_recorded_too_early": audit_row.get(
                "minutes_recorded_too_early", pd.NA
            ),
            "timing_status": status,
            "candidate_eligible_for_next_backtest": eligible,
            "fill_note": (
                "M15 candle range touches entry level; exact fill price and intrabar "
                "sequence are unknown from OHLC alone."
            ),
        }
        review_rows.append(row)

    review = pd.DataFrame(review_rows)
    candidates = review[review["candidate_eligible_for_next_backtest"]].copy()

    OUT.mkdir(parents=True, exist_ok=True)
    review.to_csv(REVIEW_FILE, index=False)
    candidates.to_csv(CANDIDATES_FILE, index=False)

    print("\n===== CORRECTION SUMMARY =====")
    print(f"Original signals                         : {len(review):,}")
    print(f"Candidates with future entry-level retest: {len(candidates):,}")
    print(f"No future/valid entry retest             : {len(review) - len(candidates):,}")
    print("\nTiming status:")
    print(review["timing_status"].value_counts(dropna=False).to_string())
    print(f"\nSaved full review: {REVIEW_FILE}")
    print(f"Saved candidates : {CANDIDATES_FILE}")
    print(
        "\nNo original SMC files were modified. These are entry-level-touch candidates, "
        "not yet verified fills or final backtest trades."
    )


if __name__ == "__main__":
    main()
