"""
Download 10 years of GBPUSD M15 candles from MetaTrader 5.

Output (new file only):
  data/GBPUSD_M15_10Y.csv
  data/GBPUSD_M15_10Y_quality_report.txt

The script refuses to overwrite either output. Existing market data and strategy files
are not modified.

Notes:
- Availability depends on the broker/server and MT5 terminal's historical bar limits.
- Timestamps are saved as UTC-naive strings after conversion from MT5 epoch timestamps.
- Gaps may represent weekends, holidays, sessions, or unavailable broker history.
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone
import getpass
import time

import MetaTrader5 as mt5
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_CSV = DATA_DIR / "GBPUSD_M15_10Y.csv"
OUTPUT_REPORT = DATA_DIR / "GBPUSD_M15_10Y_quality_report.txt"

TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
YEARS_BACK = 10
BATCH_DAYS = 90
TIMEFRAME = mt5.TIMEFRAME_M15


def choose_symbol():
    symbols = mt5.symbols_get()
    if symbols is None:
        raise RuntimeError(f"Could not list MT5 symbols: {mt5.last_error()}")

    candidates = []
    for symbol in symbols:
        name = symbol.name
        if "GBPUSD" in name.upper():
            candidates.append((name, bool(symbol.visible), getattr(symbol, "path", "")))

    print("\nGBPUSD-like symbols on this server:")
    for name, visible, path in candidates:
        print(f"  {name} | visible={visible} | path={path}")

    if not candidates:
        raise RuntimeError(
            "No GBPUSD-like symbol found. Check that your broker offers GBPUSD."
        )

    if len(candidates) == 1:
        selected = candidates[0][0]
        print(f"\nUsing symbol: {selected}")
        return selected

    available_names = {row[0] for row in candidates}
    selected = input(
        "\nEnter the exact GBPUSD symbol name from the list above: "
    ).strip()
    if selected not in available_names:
        raise ValueError("Selected symbol is not in the displayed candidate list.")
    return selected


def fetch_range(symbol, start_utc, end_utc):
    chunks = []
    cursor = start_utc
    total = 0

    while cursor < end_utc:
        batch_end = min(cursor + timedelta(days=BATCH_DAYS), end_utc)
        rates = mt5.copy_rates_range(symbol, TIMEFRAME, cursor, batch_end)

        if rates is None:
            print(
                f"WARNING: request failed for {cursor} to {batch_end}: "
                f"{mt5.last_error()}"
            )
        elif len(rates) > 0:
            frame = pd.DataFrame(rates)
            frame["time"] = pd.to_datetime(
                frame["time"], unit="s", utc=True
            ).dt.tz_localize(None)
            chunks.append(frame)
            total += len(frame)
            print(
                f"Fetched {len(frame):,} candles "
                f"({total:,} so far): {frame['time'].min()} -> {frame['time'].max()}"
            )
        else:
            print(f"No candles returned for {cursor.date()} -> {batch_end.date()}")

        cursor = batch_end
        time.sleep(0.1)

    if not chunks:
        raise RuntimeError(
            "MT5 returned no candles. Check the symbol, account connection, "
            "terminal history limits, and broker data availability."
        )

    return pd.concat(chunks, ignore_index=True)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_CSV.exists():
        raise FileExistsError(
            f"{OUTPUT_CSV} already exists. It will not be overwritten. "
            "Rename the existing file or change OUTPUT_CSV in this script."
        )
    if OUTPUT_REPORT.exists():
        raise FileExistsError(
            f"{OUTPUT_REPORT} already exists. It will not be overwritten. "
            "Rename it or change OUTPUT_REPORT in this script."
        )

    login_text = input("Enter MT5 numeric account login: ").strip()
    if not login_text.isdigit():
        raise ValueError("MT5 login must be numeric.")
    login = int(login_text)
    server = input("Enter exact MT5 server name (e.g. MetaQuotes-Demo): ").strip()
    password = getpass.getpass("Enter MT5 password (input hidden): ")

    initialized = mt5.initialize(
        path=TERMINAL_PATH,
        login=login,
        password=password,
        server=server,
        timeout=60000,
    )
    if not initialized:
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")

    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise RuntimeError("MT5 terminal/account is not authenticated.")
        if account.login != login:
            raise RuntimeError("Connected account login does not match the requested login.")

        print(f"\nConnected to server: {account.server}")
        print(f"Terminal: {terminal.name}")
        symbol = choose_symbol()

        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"symbol_info failed for {symbol}: {mt5.last_error()}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")

        end_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        start_utc = end_utc - timedelta(days=365 * YEARS_BACK)

        print(f"\nRequested UTC range: {start_utc} -> {end_utc}")
        print("Downloading M15 history in 90-day batches...")
        df = fetch_range(symbol, start_utc, end_utc)

        keep = [
            column for column in [
                "time", "open", "high", "low", "close",
                "tick_volume", "spread", "real_volume"
            ] if column in df.columns
        ]
        df = df[keep].copy()
        df = df.dropna(subset=["time", "open", "high", "low", "close"])
        df = (
            df.sort_values("time")
              .drop_duplicates("time", keep="last")
              .reset_index(drop=True)
        )

        if df.empty:
            raise RuntimeError("No valid candles remain after cleaning.")

        timestamps = pd.to_datetime(df["time"])
        differences = timestamps.diff().dropna()
        gaps = differences[differences > pd.Timedelta(minutes=15)]
        gap_counts = gaps.value_counts().sort_index()
        years_covered = (timestamps.max() - timestamps.min()).total_seconds() / (365.25 * 86400)

        report = [
            "GBPUSD M15 TEN-YEAR HISTORICAL DATA QUALITY REPORT",
            "=" * 55,
            f"Server: {account.server}",
            f"MT5 symbol: {symbol}",
            "Timeframe: M15",
            f"Requested start UTC: {start_utc}",
            f"Requested end UTC: {end_utc}",
            f"Actual first candle: {timestamps.min()}",
            f"Actual last candle: {timestamps.max()}",
            f"Rows saved: {len(df):,}",
            f"Approximate calendar span in years: {years_covered:.2f}",
            f"Duplicate timestamps after cleanup: {int(timestamps.duplicated().sum())}",
            f"Transitions greater than 15 minutes: {len(gaps):,}",
            "",
            "Largest timestamp gaps (may be normal market closures):",
        ]
        if gap_counts.empty:
            report.append("None")
        else:
            for duration, count in gap_counts.items():
                report.append(f"{duration}: {int(count)} transitions")
        report.extend([
            "",
            "Caveats:",
            "- This report does not assume every gap is a missing candle.",
            "- Weekends, holidays, broker sessions and terminal history limits affect coverage.",
            "- Compare this dataset with the existing GBPUSD files before using it in backtests.",
        ])

        # The pre-check above ensures these are new output files.
        df.to_csv(OUTPUT_CSV, index=False)
        OUTPUT_REPORT.write_text("\n".join(report), encoding="utf-8")

        print("\n" + "\n".join(report))
        print(f"\nSaved data: {OUTPUT_CSV}")
        print(f"Saved report: {OUTPUT_REPORT}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
