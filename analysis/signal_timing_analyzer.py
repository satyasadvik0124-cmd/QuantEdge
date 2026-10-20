"""
QuantEdge Signal Timing Audit
-----------------------------

Audits existing SMC signals for timing/look-ahead risks without modifying the
original signal generator or any existing output files.

Run from the project root:
    python analysis/signal_timing_analyzer.py

The report is written to:
    outputs/signal_timing_audit.csv

Important:
- OHLC timestamps are assumed to be candle-open timestamps.
- For M15 data, a candle's high/low/close are treated as known only after
  its close, i.e. timestamp + 15 minutes.
- The current signal generator records the order-block candle timestamp as
  signal_time, even though CHOCH and FVG information may occur later.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Make the project root importable when this file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config import PAIR, TIMEFRAME_NAME, HISTORICAL_FILE
except Exception as exc:
    raise SystemExit(
        "Could not import config.py. Run this script from within the QuantEdge "
        f"project and check config.py. Details: {exc}"
    )

OUTPUT_DIR = PROJECT_ROOT / "outputs"
SIGNALS_FILE = OUTPUT_DIR / "signals_v3.csv"
SWEEPS_FILE = OUTPUT_DIR / "validated_sweeps_v2.csv"
OBS_FILE = OUTPUT_DIR / "order_blocks_v1.csv"
FVGS_FILE = OUTPUT_DIR / "fvg_v2.csv"
REPORT_FILE = OUTPUT_DIR / "signal_timing_audit.csv"

TIMEFRAME_MINUTES = 15
MAX_OB_AGE_DAYS = 7


def read_csv_required(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    frame = pd.read_csv(path)
    missing = required_columns.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{path.name} is missing required columns: {sorted(missing)}. "
            f"Available columns: {list(frame.columns)}"
        )
    return frame


def parse_times(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def timestamp_after_candle_close(value: Any) -> pd.Timestamp:
    """Treat stored timestamps as candle-open times; information is known at close."""
    return pd.Timestamp(value) + pd.Timedelta(minutes=TIMEFRAME_MINUTES)


def entry_touched(direction: str, candle: pd.Series, entry: float) -> bool:
    """
    Check whether price traded through the candidate entry level.

    For a BUY limit at the OB high, a later candle low at/below entry indicates
    the level was reached. For a SELL limit at the OB low, a later candle high
    at/above entry indicates the level was reached.
    """
    if direction == "BUY":
        return float(candle["low"]) <= entry
    if direction == "SELL":
        return float(candle["high"]) >= entry
    return False


def find_component_combinations(
    signal: pd.Series,
    sweeps: pd.DataFrame,
    obs: pd.DataFrame,
    fvgs: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Reconstruct plausible sweep/CHOCH/OB/FVG combinations for one signal."""
    direction = str(signal["direction"]).upper()
    signal_time = pd.Timestamp(signal["signal_time"])

    if direction == "BUY":
        sweep_type = "SSL_SWEEP"
        ob_type = "BULLISH_OB"
        fvg_type = "BULLISH_FVG"
    elif direction == "SELL":
        sweep_type = "BSL_SWEEP"
        ob_type = "BEARISH_OB"
        fvg_type = "BEARISH_FVG"
    else:
        return []

    signal_obs = obs[
        (obs["type"] == ob_type)
        & (obs["time"] == signal_time)
    ]
    if signal_obs.empty:
        return []

    relevant_sweeps = sweeps[sweeps["type"] == sweep_type]
    relevant_fvgs = fvgs[fvgs["type"] == fvg_type]
    combinations: list[dict[str, Any]] = []

    for _, sweep in relevant_sweeps.iterrows():
        sweep_time = sweep["sweep_time"]
        choch_time = sweep["choch_time"]

        if pd.isna(sweep_time) or pd.isna(choch_time):
            continue
        if choch_time < sweep_time:
            continue

        # Match the original generator's OB selection: the closest eligible
        # same-direction OB at or before CHOCH, within seven days.
        eligible_obs = obs[
            (obs["type"] == ob_type)
            & (obs["time"] <= choch_time)
        ].copy()
        if eligible_obs.empty:
            continue

        eligible_obs["ob_age"] = choch_time - eligible_obs["time"]
        eligible_obs = eligible_obs[
            eligible_obs["ob_age"] <= pd.Timedelta(days=MAX_OB_AGE_DAYS)
        ]
        if eligible_obs.empty:
            continue

        chosen_ob = eligible_obs.sort_values("ob_age").iloc[0]
        if pd.Timestamp(chosen_ob["time"]) != signal_time:
            continue

        eligible_fvgs = relevant_fvgs[
            (relevant_fvgs["time"] >= chosen_ob["time"])
            & (
                relevant_fvgs["time"]
                <= chosen_ob["time"] + pd.Timedelta(days=MAX_OB_AGE_DAYS)
            )
        ]
        if eligible_fvgs.empty:
            continue

        # The original generator only requires at least one eligible FVG.
        # Earliest such FVG gives the earliest possible availability time.
        for _, fvg in eligible_fvgs.iterrows():
            component_times = [
                pd.Timestamp(sweep_time),
                pd.Timestamp(choch_time),
                pd.Timestamp(chosen_ob["time"]),
                pd.Timestamp(fvg["time"]),
            ]
            available_time = max(
                timestamp_after_candle_close(t) for t in component_times
            )

            combinations.append({
                "sweep_time": sweep_time,
                "choch_time": choch_time,
                "ob_time": chosen_ob["time"],
                "fvg_time": fvg["time"],
                "available_time": available_time,
            })

    return combinations


def main() -> None:
    print("\n===== QUANTEDGE SIGNAL TIMING AUDIT =====")
    print(f"Configured asset: {PAIR}_{TIMEFRAME_NAME}")
    print(f"Historical data:  {HISTORICAL_FILE}")

    if not Path(HISTORICAL_FILE).exists():
        raise SystemExit(
            f"Historical data file does not exist: {HISTORICAL_FILE}\n"
            "Check PAIR in config.py and confirm the matching CSV is in data/."
        )

    data = read_csv_required(
        Path(HISTORICAL_FILE),
        {"time", "open", "high", "low", "close"},
    )
    signals = read_csv_required(
        SIGNALS_FILE,
        {"signal_time", "direction", "entry", "sl", "tp"},
    )
    sweeps = read_csv_required(
        SWEEPS_FILE,
        {"sweep_time", "choch_time", "type"},
    )
    obs = read_csv_required(
        OBS_FILE,
        {"time", "type", "high", "low"},
    )
    fvgs = read_csv_required(
        FVGS_FILE,
        {"time", "type"},
    )

    data = parse_times(data, ["time"]).dropna(subset=["time"])
    signals = parse_times(signals, ["signal_time"]).dropna(subset=["signal_time"])
    sweeps = parse_times(sweeps, ["sweep_time", "choch_time"]).dropna(
        subset=["sweep_time", "choch_time"]
    )
    obs = parse_times(obs, ["time"]).dropna(subset=["time"])
    fvgs = parse_times(fvgs, ["time"]).dropna(subset=["time"])

    data = data.sort_values("time").reset_index(drop=True)
    signals = signals.sort_values("signal_time").reset_index(drop=True)

    if signals.empty:
        raise SystemExit(f"No signals found in {SIGNALS_FILE}")

    rows: list[dict[str, Any]] = []

    for signal_id, signal in signals.iterrows():
        signal_time = pd.Timestamp(signal["signal_time"])
        direction = str(signal["direction"]).upper()
        entry = float(signal["entry"])

        combos = find_component_combinations(signal, sweeps, obs, fvgs)

        base: dict[str, Any] = {
            "signal_id": signal_id,
            "recorded_signal_time": signal_time,
            "direction": direction,
            "entry": entry,
            "sl": float(signal["sl"]),
            "tp": float(signal["tp"]),
            "component_match_found": bool(combos),
        }

        if not combos:
            rows.append({
                **base,
                "matched_sweep_time": pd.NaT,
                "matched_choch_time": pd.NaT,
                "matched_ob_time": pd.NaT,
                "matched_fvg_time": pd.NaT,
                "earliest_valid_available_time": pd.NaT,
                "minutes_recorded_too_early": pd.NA,
                "entry_touched_before_available": pd.NA,
                "first_entry_touch_after_available": pd.NaT,
                "timing_status": "UNVERIFIED_COMPONENT_MATCH",
                "audit_note": (
                    "Could not reconstruct a matching sweep/CHOCH/OB/FVG chain "
                    "from current output files. The signal CSV does not store "
                    "component IDs, so this row requires manual inspection."
                ),
            })
            continue

        # Use the earliest availability among valid reconstructed combinations.
        combo = min(combos, key=lambda item: item["available_time"])
        available_time = pd.Timestamp(combo["available_time"])
        delay_minutes = max(
            0.0, (available_time - signal_time).total_seconds() / 60.0
        )

        # Candles after the recorded OB timestamp but before the signal could
        # actually be known. If the level was touched, a later entry at that
        # level would not be a valid fresh entry unless the strategy explicitly
        # supports re-entry.
        between = data[
            (data["time"] > signal_time)
            & (data["time"] < available_time)
        ]
        touched_before = any(
            entry_touched(direction, candle, entry)
            for _, candle in between.iterrows()
        )

        after = data[data["time"] >= available_time]
        first_touch = pd.NaT
        for _, candle in after.iterrows():
            if entry_touched(direction, candle, entry):
                first_touch = pd.Timestamp(candle["time"])
                break

        if available_time > signal_time:
            timing_status = "RECORDED_TOO_EARLY"
        else:
            timing_status = "TIMESTAMP_OK_CHECK_ENTRY"

        if touched_before:
            timing_status += "|ENTRY_LEVEL_TOUCHED_BEFORE_AVAILABLE"

        if pd.isna(first_touch):
            timing_status += "|NO_FUTURE_ENTRY_TOUCH_IN_DATA"

        rows.append({
            **base,
            "matched_sweep_time": combo["sweep_time"],
            "matched_choch_time": combo["choch_time"],
            "matched_ob_time": combo["ob_time"],
            "matched_fvg_time": combo["fvg_time"],
            "earliest_valid_available_time": available_time,
            "minutes_recorded_too_early": round(delay_minutes, 2),
            "entry_touched_before_available": touched_before,
            "first_entry_touch_after_available": first_touch,
            "timing_status": timing_status,
            "audit_note": (
                "Availability is conservatively estimated at the close of the "
                "latest required M15 candle. Confirm actual detector semantics "
                "before using this report to change the strategy."
            ),
        })

    report = pd.DataFrame(rows)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(REPORT_FILE, index=False)

    verified = report[report["component_match_found"] == True]  # noqa: E712
    too_early = verified[
        verified["timing_status"].astype(str).str.contains("RECORDED_TOO_EARLY")
    ]
    touched = verified[
        verified["entry_touched_before_available"].fillna(False).astype(bool)
    ]
    unverified = report[report["component_match_found"] != True]  # noqa: E712

    print("\n===== AUDIT SUMMARY =====")
    print(f"Signals audited                     : {len(report):,}")
    print(f"Signals with reconstructed components: {len(verified):,}")
    print(f"Signals requiring manual matching    : {len(unverified):,}")
    print(f"Recorded earlier than availability   : {len(too_early):,}")
    print(f"Entry level touched before available : {len(touched):,}")
    print(f"\nSaved report: {REPORT_FILE}")
    print(
        "\nThis is an audit only. It does not edit signals, change the SMC rules, "
        "or retrain any model."
    )


if __name__ == "__main__":
    main()
