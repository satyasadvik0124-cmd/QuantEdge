"""
=========================================================
QuantEdge V2
Liquidity Sweep Detector V2
=========================================================

Detects

EQH → BSL Sweep

EQL → SSL Sweep

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class LiquiditySweepDetector:

    def __init__(self):

        self.bullish_sweeps = 0
        self.bearish_sweeps = 0

    # =====================================================
    # Detect Liquidity Sweeps
    # =====================================================

    def run(
        self,
        df: pd.DataFrame,
        save_output=False
    ) -> pd.DataFrame:

        df = df.copy()

        # -----------------------------------------
        # Initialize Columns
        # -----------------------------------------

        df["liquidity_sweep"] = False
        df["sweep_type"] = None
        df["sweep_price"] = None

        # -----------------------------------------
        # Liquidity Levels
        # -----------------------------------------

        liquidity = df[
            df["liquidity"] == True
        ].copy()

        liquidity = liquidity.reset_index()

        liquidity.rename(
            columns={
                "index": "candle_index"
            },
            inplace=True
        )

        sweeps = []

        self.bullish_sweeps = 0
        self.bearish_sweeps = 0

        # -----------------------------------------
        # Sweep Detection
        # -----------------------------------------
        for _, level in liquidity.iterrows():

            liquidity_time = level["time"]
            liquidity_price = level["liquidity_price"]
            liquidity_type = level["liquidity_type"]

            future_candles = df[
                df["time"] > liquidity_time
            ]

            # =====================================
            # EQH → BSL Sweep
            # =====================================

            if liquidity_type == "EQH":

                for idx, candle in future_candles.iterrows():

                    if (

                        candle["high"] > liquidity_price

                        and

                        candle["close"] < liquidity_price

                    ):

                        df.loc[
                            idx,
                            "liquidity_sweep"
                        ] = True

                        df.loc[
                            idx,
                            "sweep_type"
                        ] = "BSL_SWEEP"

                        df.loc[
                            idx,
                            "sweep_price"
                        ] = liquidity_price

                        sweeps.append({

                            "time": candle["time"],
                            "type": "BSL_SWEEP",
                            "price": liquidity_price

                        })

                        self.bearish_sweeps += 1

                        break

            # =====================================
            # EQL → SSL Sweep
            # =====================================

            elif liquidity_type == "EQL":

                for idx, candle in future_candles.iterrows():

                    if (

                        candle["low"] < liquidity_price

                        and

                        candle["close"] > liquidity_price

                    ):

                        df.loc[
                            idx,
                            "liquidity_sweep"
                        ] = True

                        df.loc[
                            idx,
                            "sweep_type"
                        ] = "SSL_SWEEP"

                        df.loc[
                            idx,
                            "sweep_price"
                        ] = liquidity_price

                        sweeps.append({

                            "time": candle["time"],
                            "type": "SSL_SWEEP",
                            "price": liquidity_price

                        })

                        self.bullish_sweeps += 1

                        break

        # -----------------------------------------
        # Remove Duplicates
        # -----------------------------------------

        sweeps_df = pd.DataFrame(
            sweeps
        )

        if not sweeps_df.empty:

            sweeps_df = (
                sweeps_df
                .drop_duplicates()
                .reset_index(
                    drop=True
                )
            )

        # -----------------------------------------
        # Optional CSV Export
        # -----------------------------------------

        if save_output:

            Path(
                OUTPUT_FOLDER
            ).mkdir(
                exist_ok=True
            )

            sweeps_df.to_csv(

                f"{OUTPUT_FOLDER}/liquidity_sweeps_v2.csv",

                index=False

            )

        return df
        # =====================================================
    # Get Sweep Events
    # =====================================================

    def get_sweeps(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        sweeps = df[
            df["liquidity_sweep"] == True
        ].copy()

        return sweeps.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        sweeps = self.get_sweeps(df)

        total = (
            self.bullish_sweeps
            + self.bearish_sweeps
        )

        liquidity_count = len(
            df[df["liquidity"] == True]
        )

        print()

        print("=" * 60)
        print("LIQUIDITY SWEEP DETECTOR V2 REPORT")
        print("=" * 60)

        print(f"Bullish Sweeps : {self.bullish_sweeps:,}")
        print(f"Bearish Sweeps : {self.bearish_sweeps:,}")
        print(f"Total Sweeps   : {total:,}")

        if liquidity_count > 0:

            rate = (
                total / liquidity_count
            ) * 100

            print(f"Sweep Rate     : {rate:.2f}%")

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        sweeps = self.get_sweeps(df)

        print("\nFirst 20 Sweep Events\n")

        if sweeps.empty:

            print("No Sweep Events Found.")
            return

        print(

            sweeps[
                [
                    "index",
                    "time",
                    "sweep_type",
                    "sweep_price"
                ]
            ].head(20)

        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from config import HISTORICAL_FILE

    from analysis.swing_detector_v3 import SwingDetector
    from analysis.market_structure_v4 import MarketStructure
    from analysis.liquidity_detector_v2 import LiquidityDetector

    print("=" * 60)
    print("QUANTEDGE LIQUIDITY SWEEP DETECTOR V2")
    print("=" * 60)

    # ---------------------------------------------
    # Load Historical Data
    # ---------------------------------------------

    df = pd.read_csv(
        HISTORICAL_FILE
    )

    print(
        f"Candles Loaded : {len(df):,}"
    )

    # ---------------------------------------------
    # Swing Detector
    # ---------------------------------------------

    swing = SwingDetector()

    df = swing.run(df)

    # ---------------------------------------------
    # Market Structure
    # ---------------------------------------------

    structure = MarketStructure()

    df = structure.run(df)

    # ---------------------------------------------
    # Liquidity Detector
    # ---------------------------------------------

    liquidity = LiquidityDetector()

    df = liquidity.run(df)

    # ---------------------------------------------
    # Sweep Detector
    # ---------------------------------------------

    sweep = LiquiditySweepDetector()

    df = sweep.run(
        df,
        save_output=True
    )

    sweep.report(df)

    sweep.summary(df)

    print("\nValidation Complete")

    print("=" * 60)