"""
=========================================================
QuantEdge V2
5-Year Historical MT5 Data Collector
=========================================================

Downloads XAUUSD M15 historical OHLCV data from MT5
in smaller chunks and combines them into one CSV.

Output:
data/XAUUSD_M15_5Y.csv
=========================================================
"""

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

import sys
import os


# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)


# =========================================================
# CONFIGURATION
# =========================================================

PAIR = "XAUUSD"

TIMEFRAME = mt5.TIMEFRAME_M15

TIMEFRAME_NAME = "M15"

MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"

DATA_FOLDER = Path(
    PROJECT_ROOT
) / "data"

HISTORICAL_FILE = (
    DATA_FOLDER /
    f"{PAIR}_{TIMEFRAME_NAME}_5Y.csv"
)

# Download six months at a time
CHUNK_MONTHS = 6


# =========================================================
# COLLECTOR
# =========================================================

class MT5Collector:

    def __init__(self):

        # Use UTC
        self.end_date = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        # Five years
        self.start_date = (
            self.end_date
            - relativedelta(years=5)
        )


    # =====================================================
    # CONNECT
    # =====================================================

    def connect(self):

        print("\n")
        print("=" * 60)
        print("CONNECTING TO METATRADER 5")
        print("=" * 60)

        print(
            f"Terminal : {MT5_PATH}"
        )

        if not os.path.exists(MT5_PATH):

            raise FileNotFoundError(
                f"\nMT5 terminal not found:\n"
                f"{MT5_PATH}"
            )


        if not mt5.initialize(
            path=MT5_PATH,
            timeout=60000
        ):

            raise RuntimeError(
                "\nMT5 initialization failed.\n"
                f"Error: {mt5.last_error()}"
            )


        print(
            "MT5 initialized successfully."
        )


        # =================================================
        # ACCOUNT
        # =================================================

        account = mt5.account_info()

        if account is None:

            error = mt5.last_error()

            mt5.shutdown()

            raise RuntimeError(
                "\nAccount information unavailable.\n"
                f"Error: {error}"
            )


        print(
            f"Login         : {account.login}"
        )

        print(
            f"Server        : {account.server}"
        )

        print(
            f"Balance       : {account.balance}"
        )


        # =================================================
        # SYMBOL
        # =================================================

        if not mt5.symbol_select(
            PAIR,
            True
        ):

            error = mt5.last_error()

            mt5.shutdown()

            raise RuntimeError(
                f"\nFailed to select {PAIR}.\n"
                f"Error: {error}"
            )


        print(
            f"Symbol selected successfully: {PAIR}"
        )


    # =====================================================
    # DISCONNECT
    # =====================================================

    def disconnect(self):

        mt5.shutdown()

        print(
            "\nMT5 connection closed."
        )


    # =====================================================
    # DOWNLOAD ONE CHUNK
    # =====================================================

    def download_chunk(
        self,
        chunk_start,
        chunk_end,
        chunk_number
    ):

        print("\n")
        print("-" * 60)

        print(
            f"CHUNK {chunk_number}"
        )

        print(
            f"Start : {chunk_start}"
        )

        print(
            f"End   : {chunk_end}"
        )

        print("-" * 60)


        rates = mt5.copy_rates_range(
            PAIR,
            TIMEFRAME,
            chunk_start,
            chunk_end
        )


        # =================================================
        # CHECK RESULT
        # =================================================

        if rates is None:

            error = mt5.last_error()

            raise RuntimeError(
                f"\nFailed downloading chunk "
                f"{chunk_number}\n"
                f"Period: {chunk_start} -> {chunk_end}\n"
                f"MT5 Error: {error}"
            )


        if len(rates) == 0:

            print(
                f"WARNING: Chunk {chunk_number} "
                f"returned 0 candles."
            )

            return pd.DataFrame()


        # =================================================
        # DATAFRAME
        # =================================================

        df = pd.DataFrame(
            rates
        )


        # =================================================
        # TIME
        # =================================================

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s"
        )


        # =================================================
        # SORT
        # =================================================

        df = (
            df
            .sort_values(
                "time"
            )
            .reset_index(
                drop=True
            )
        )


        print(
            f"Candles: {len(df):,}"
        )

        print(
            f"Actual : "
            f"{df['time'].min()} "
            f"-> "
            f"{df['time'].max()}"
        )


        return df


    # =====================================================
    # COLLECT ALL 5 YEARS
    # =====================================================

    def collect(self):

        connected = False

        try:

            # =============================================
            # CONNECT
            # =============================================

            self.connect()

            connected = True


            print("\n")
            print("=" * 60)
            print("5-YEAR HISTORICAL DOWNLOAD")
            print("=" * 60)

            print(
                f"Symbol       : {PAIR}"
            )

            print(
                f"Timeframe    : {TIMEFRAME_NAME}"
            )

            print(
                f"Start        : {self.start_date}"
            )

            print(
                f"End          : {self.end_date}"
            )

            print(
                f"Chunk Size   : {CHUNK_MONTHS} months"
            )

            print("=" * 60)


            # =============================================
            # CREATE CHUNKS
            # =============================================

            chunks = []

            current_start = self.start_date

            chunk_number = 1


            while current_start < self.end_date:

                current_end = (
                    current_start
                    + relativedelta(
                        months=CHUNK_MONTHS
                    )
                )


                if current_end > self.end_date:

                    current_end = self.end_date


                # =========================================
                # DOWNLOAD
                # =========================================

                df_chunk = self.download_chunk(
                    current_start,
                    current_end,
                    chunk_number
                )


                if not df_chunk.empty:

                    chunks.append(
                        df_chunk
                    )


                # =========================================
                # NEXT CHUNK
                # =========================================

                current_start = current_end

                chunk_number += 1


            # =============================================
            # CHECK
            # =============================================

            if not chunks:

                raise RuntimeError(
                    "\nNo historical data was downloaded."
                )


            # =============================================
            # COMBINE
            # =============================================

            print("\n")
            print("=" * 60)
            print("COMBINING DATA")
            print("=" * 60)


            df = pd.concat(
                chunks,
                ignore_index=True
            )


            # =============================================
            # REMOVE DUPLICATES
            # =============================================

            df = (
                df
                .drop_duplicates(
                    subset=["time"]
                )
                .sort_values(
                    "time"
                )
                .reset_index(
                    drop=True
                )
            )


            # =============================================
            # CREATE DATA DIRECTORY
            # =============================================

            DATA_FOLDER.mkdir(
                parents=True,
                exist_ok=True
            )


            # =============================================
            # SAVE
            # =============================================

            df.to_csv(
                HISTORICAL_FILE,
                index=False
            )


            # =============================================
            # ACTUAL PERIOD
            # =============================================

            actual_days = (
                df["time"].max()
                - df["time"].min()
            ).days


            actual_years = (
                actual_days / 365.25
            )


            # =============================================
            # FINAL REPORT
            # =============================================

            print("\n")
            print("=" * 60)
            print("DOWNLOAD COMPLETE")
            print("=" * 60)

            print(
                f"Pair        : {PAIR}"
            )

            print(
                f"Timeframe   : {TIMEFRAME_NAME}"
            )

            print(
                f"Total Candles: {len(df):,}"
            )

            print(
                f"Start       : {df['time'].min()}"
            )

            print(
                f"End         : {df['time'].max()}"
            )

            print(
                f"Actual Years: {actual_years:.2f}"
            )

            print(
                f"Saved To    : {HISTORICAL_FILE}"
            )

            print("=" * 60)


            # =============================================
            # VALIDATE
            # =============================================

            if actual_years >= 4.9:

                print(
                    "\nSUCCESS:"
                )

                print(
                    "Approximately 5 years of "
                    "XAUUSD M15 data collected."
                )

            else:

                print(
                    "\nWARNING:"
                )

                print(
                    "Less than 5 years of history "
                    "was returned by MT5."
                )


            # =============================================
            # FIRST / LAST
            # =============================================

            print("\nFIRST 5 CANDLES")
            print("-" * 60)

            print(
                df.head()
            )


            print("\nLAST 5 CANDLES")
            print("-" * 60)

            print(
                df.tail()
            )


            return df


        finally:

            if connected:

                self.disconnect()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 60)
    print("QUANTEDGE V2")
    print("5-YEAR XAUUSD M15 HISTORICAL DATA COLLECTOR")
    print("=" * 60)


    collector = MT5Collector()


    try:

        collector.collect()


        print("\n")
        print("=" * 60)
        print("COLLECTION FINISHED SUCCESSFULLY")
        print("=" * 60)


    except Exception as e:

        print("\n")
        print("=" * 60)
        print("COLLECTION FAILED")
        print("=" * 60)

        print(
            f"\nError:\n{e}"
        )

        print("=" * 60)

        sys.exit(1)