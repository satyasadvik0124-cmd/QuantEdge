"""Fetch completed MT5 M15 candles for QuantEdge diagnostics.

Run from the QuantEdge project root:
    python .\\analysis\\get_live_mt5_snapshot.py

This script only fetches and saves candles. It does NOT generate trades, change
strategy settings, or place orders.

Some broker/terminal setups can return bar timestamps that behave like broker
server time rather than UTC. The script checks for timestamps that are in the
future relative to the computer's UTC clock and, only when a whole-hour offset
can be validated against the latest completed M15 bar, normalizes the timestamps.
It logs the detected adjustment. It does not alter OHLC prices or candle order.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys

try:
    import MetaTrader5 as mt5
    import pandas as pd
except ImportError as exc:
    print(f"Missing dependency: {exc}")
    print("Install into the same Python environment with:")
    print("  python -m pip install MetaTrader5 pandas")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "ml" / "live_snapshot"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TIMEFRAME_MINUTES = 15


def resolve_symbol(candidates):
    available = mt5.symbols_get()
    if available is None:
        return None
    names = [s.name for s in available]
    for candidate in candidates:
        if candidate in names:
            return candidate
    # Broker suffix/prefix fallback, only if unambiguous.
    for candidate in candidates:
        matches = [name for name in names if candidate in name]
        if len(matches) == 1:
            return matches[0]
    return None


def normalize_mt5_times(df, now_utc, pair):
    """Convert MT5 epoch values to UTC and correct a validated future offset.

    MT5 normally returns UTC epoch timestamps. This guard handles terminals where
    the latest returned bar is clearly future-dated, e.g. 21:00 when UTC is 18:23.
    We infer only whole-hour offsets and accept a correction only if the corrected
    latest bar matches the expected most-recent completed M15 bar within one bar.
    Otherwise, leave the timestamps untouched and warn instead of guessing.
    """
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    if df.empty:
        return df

    raw_latest = df["time"].iloc[-1]
    # Most recent completed M15 candle's opening time, in UTC.
    minute_floor = (now_utc.minute // TIMEFRAME_MINUTES) * TIMEFRAME_MINUTES
    expected_latest = now_utc.replace(minute=minute_floor, second=0, microsecond=0) - timedelta(minutes=TIMEFRAME_MINUTES)
    expected_latest = pd.Timestamp(expected_latest)

    future_by = (raw_latest - pd.Timestamp(now_utc)).total_seconds()
    if future_by > TIMEFRAME_MINUTES * 60:
        delta_hours = round((raw_latest - expected_latest).total_seconds() / 3600)
        if delta_hours != 0:
            adjusted_latest = raw_latest - pd.Timedelta(hours=delta_hours)
            distance_minutes = abs((adjusted_latest - expected_latest).total_seconds()) / 60
            if distance_minutes <= TIMEFRAME_MINUTES:
                df["time"] = df["time"] - pd.Timedelta(hours=delta_hours)
                print(
                    f"{pair}: timestamp adjustment applied: -{delta_hours} hour(s). "
                    f"Raw latest={raw_latest}; normalized latest={df['time'].iloc[-1]} UTC."
                )
            else:
                print(
                    f"WARNING {pair}: latest MT5 candle ({raw_latest}) is future-dated, "
                    "but no reliable whole-hour correction was validated. "
                    "Timestamps were NOT changed; do not use this snapshot for signals."
                )
        else:
            print(
                f"WARNING {pair}: latest MT5 candle ({raw_latest}) is future-dated. "
                "No safe timestamp correction was found; timestamps were NOT changed."
            )
    else:
        # Detect stale/missing data without trying to shift it.
        age_minutes = (expected_latest - raw_latest).total_seconds() / 60
        if age_minutes > 2 * TIMEFRAME_MINUTES:
            print(
                f"WARNING {pair}: latest candle is {age_minutes:.0f} minutes older "
                "than the expected latest completed M15 candle. Check market hours/data feed."
            )

    return df


def main():
    if not mt5.initialize():
        print("MT5 initialize failed:", mt5.last_error())
        print("Open the MT5 desktop terminal, log in, then retry.")
        sys.exit(2)

    try:
        info = mt5.terminal_info()
        account = mt5.account_info()
        now_utc = datetime.now(timezone.utc)
        print("Computer local time:", datetime.now().astimezone().isoformat())
        print("Computer UTC time:", now_utc.isoformat())
        print("MT5 connected:", info is not None)
        print("Terminal:", getattr(info, "name", "unknown"))
        print("Account logged in:", account is not None)
        if account is not None:
            print("Account server:", account.server)
            print("Account currency:", account.currency)
            print("Account trade mode:", account.trade_mode, "(no orders will be placed)")

        timeframe = mt5.TIMEFRAME_M15
        for base in ["GBPUSD", "XAUUSD"]:
            symbol = resolve_symbol([base])
            if not symbol:
                print(f"\n{base}: symbol not found or ambiguous.")
                print("In MT5 Market Watch, check the broker's exact symbol name.")
                continue

            if not mt5.symbol_select(symbol, True):
                print(f"\n{base} ({symbol}): symbol_select failed:", mt5.last_error())
                continue

            # Position 0 is the currently forming candle; fetch extra bars and remove it.
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 300)
            if rates is None or len(rates) < 3:
                print(f"\n{base} ({symbol}): could not fetch candles:", mt5.last_error())
                continue

            df = pd.DataFrame(rates)
            # Convert/check times before dropping the currently forming bar.
            df = normalize_mt5_times(df, now_utc, base)
            df = df.iloc[:-1].copy()
            df = df.rename(columns={"tick_volume": "volume"})
            df["pair"] = base
            df["mt5_symbol"] = symbol
            df["retrieved_at_utc"] = now_utc.isoformat()
            df = df[["pair", "mt5_symbol", "time", "open", "high", "low", "close",
                     "volume", "spread", "real_volume", "retrieved_at_utc"]]

            out = OUT_DIR / f"{base.lower()}_m15_latest.csv"
            df.to_csv(out, index=False)
            latest = df.iloc[-1]
            print(f"\n{base} -> MT5 symbol: {symbol}")
            print(f"Completed candles saved: {len(df)}")
            print(f"Latest completed candle UTC: {latest['time']}")
            print(f"O/H/L/C: {latest['open']} / {latest['high']} / {latest['low']} / {latest['close']}")
            print(f"Retrieved at UTC: {now_utc.isoformat()}")
            print(f"Saved: {out}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()