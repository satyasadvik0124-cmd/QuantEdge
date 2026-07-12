"""
=========================================================
QuantEdge V2
Historical MT5 Data Collector
=========================================================

Downloads historical OHLCV data from MT5
and saves it into the data directory.

Author : QuantEdge
"""

from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from collectors.mt5_connector import MT5Connector

from config import (
    PAIR,
    TIMEFRAME,
    TIMEFRAME_NAME,
    DATA_FOLDER,
    HISTORICAL_FILE,
)


class MT5Collector:

    def __init__(self):

        self.connector = MT5Connector()

        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime.now()

    # =====================================================
    # Download Historical Data
    # =====================================================

    def collect(self):

        if not self.connector.connect():
            raise RuntimeError("Unable to connect to MT5.")

        self.connector.select_symbol(PAIR)

        print("\nDownloading historical data...")
        print(f"Symbol     : {PAIR}")
        print(f"Timeframe  : {TIMEFRAME_NAME}")

        rates = mt5.copy_rates_range(
            PAIR,
            TIMEFRAME,
            self.start_date,
            self.end_date
        )

        if rates is None:
            self.connector.disconnect()
            raise RuntimeError(
                f"Failed to download data for {PAIR}"
            )

        df = pd.DataFrame(rates)

        if df.empty:
            self.connector.disconnect()
            raise RuntimeError("No historical data returned.")

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s"
        )

        df = df.sort_values("time").reset_index(drop=True)

        Path(DATA_FOLDER).mkdir(exist_ok=True)

        df.to_csv(
            HISTORICAL_FILE,
            index=False
        )

        print("\n" + "=" * 60)
        print("DOWNLOAD COMPLETE")
        print("=" * 60)
        print(f"Pair        : {PAIR}")
        print(f"Timeframe   : {TIMEFRAME_NAME}")
        print(f"Candles     : {len(df):,}")
        print(f"Start       : {df['time'].min()}")
        print(f"End         : {df['time'].max()}")
        print(f"Saved To    : {HISTORICAL_FILE}")
        print("=" * 60)

        self.connector.disconnect()

        return df


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    collector = MT5Collector()

    collector.collect()