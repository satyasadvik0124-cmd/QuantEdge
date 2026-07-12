"""
=========================================================
QuantEdge V2
Live Data Provider
=========================================================

Fetches the latest candles from MT5.

Returns:
    Pandas DataFrame

Author : QuantEdge
"""

import MetaTrader5 as mt5
import pandas as pd

from collectors.mt5_connector import MT5Connector
from config import (
    PAIR,
    TIMEFRAME,
    BARS,
    INCLUDE_CURRENT,
)


class LiveData:

    def __init__(self):

        self.connector = MT5Connector()

        if not self.connector.is_connected():
            if not self.connector.connect():
                raise RuntimeError("Unable to connect to MT5")

        self.connector.select_symbol(PAIR)

    # =====================================================
    # Fetch Latest Candles
    # =====================================================

    def get_rates(
        self,
        symbol=PAIR,
        timeframe=TIMEFRAME,
        bars=BARS,
        include_current=INCLUDE_CURRENT,
    ):

        rates = mt5.copy_rates_from_pos(
            symbol,
            timeframe,
            0,
            bars
        )

        if rates is None:
            raise RuntimeError(
                f"Failed to fetch rates for {symbol}"
            )

        df = pd.DataFrame(rates)

        if df.empty:
            raise RuntimeError(
                f"No data received for {symbol}"
            )

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s"
        )

        df = df.sort_values("time").reset_index(drop=True)

        if not include_current:
            df = df.iloc[:-1].reset_index(drop=True)

        columns = [
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
        ]

        return df[columns]


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    live = LiveData()

    df = live.get_rates()

    print("=" * 60)
    print("LIVE DATA TEST")
    print("=" * 60)

    print(df.tail())

    print("=" * 60)
    print(f"Candles : {len(df)}")
    print(f"Latest  : {df.iloc[-1]['time']}")
    print("=" * 60)