"""
=========================================================
QuantEdge V2
Validated Sweep Detector V2
=========================================================

Validates Liquidity Sweeps
using CHOCH confirmation.

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class ValidatedSweepDetector:

    def __init__(self):

        self.lookahead_minutes = 150

        self.bullish_validated = 0
        self.bearish_validated = 0

    # =====================================================
    # Validate Sweeps
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

        df["validated_sweep"] = False
        df["validated_type"] = None

        sweeps = df[
            df["liquidity_sweep"] == True
        ].copy()

        sweeps = sweeps.reset_index()

        sweeps.rename(
            columns={
                "index": "candle_index"
            },
            inplace=True
        )

        choch = df[
            df["choch"] == True
        ].copy()

        choch = choch.reset_index()

        validated = []

        self.bullish_validated = 0
        self.bearish_validated = 0

        # -----------------------------------------
        # Validation Logic
        # -----------------------------------------
        for _, sweep in sweeps.iterrows():

            sweep_time = sweep["time"]
            sweep_type = sweep["sweep_type"]

            # =====================================
            # Expected CHOCH
            # =====================================

            if sweep_type == "BSL_SWEEP":

                target_choch = "BEARISH_CHOCH"

            elif sweep_type == "SSL_SWEEP":

                target_choch = "BULLISH_CHOCH"

            else:

                continue

            matching_choch = choch[

                (choch["choch_type"] == target_choch)

                &

                (choch["time"] >= sweep_time)

                &

                (

                    choch["time"]

                    <=

                    sweep_time

                    + pd.Timedelta(
                        minutes=self.lookahead_minutes
                    )

                )

            ]

            if not matching_choch.empty:

                first_choch = matching_choch.iloc[0]

                candle = int(first_choch["index"])

                df.loc[
                    candle,
                    "validated_sweep"
                ] = True

                df.loc[
                    candle,
                    "validated_type"
                ] = sweep_type

                validated.append({

                    "sweep_time": sweep_time,
                    "choch_time": first_choch["time"],
                    "type": sweep_type,
                    "price": sweep["sweep_price"]

                })

                if sweep_type == "BSL_SWEEP":

                    self.bearish_validated += 1

                else:

                    self.bullish_validated += 1

        # -----------------------------------------
        # Remove Duplicates
        # -----------------------------------------

        validated_df = pd.DataFrame(
            validated
        )

        if not validated_df.empty:

            validated_df = (
                validated_df
                .drop_duplicates(
                    subset=[
                        "sweep_time",
                        "type"
                    ]
                )
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

            validated_df.to_csv(

                f"{OUTPUT_FOLDER}/validated_sweeps_v2.csv",

                index=False

            )

        return df
        # =====================================================
    # Get Validated Sweeps
    # =====================================================

    def get_validated_sweeps(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        validated = df[
            df["validated_sweep"] == True
        ].copy()

        return validated.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        validated = self.get_validated_sweeps(df)

        total = (
            self.bullish_validated
            + self.bearish_validated
        )

        sweep_count = len(
            df[df["liquidity_sweep"] == True]
        )

        print()

        print("=" * 60)
        print("VALIDATED SWEEP DETECTOR V2 REPORT")
        print("=" * 60)

        print(
            f"Bullish Validated Sweeps : "
            f"{self.bullish_validated:,}"
        )

        print(
            f"Bearish Validated Sweeps : "
            f"{self.bearish_validated:,}"
        )

        print(
            f"Total Validated Sweeps   : "
            f"{total:,}"
        )

        if sweep_count > 0:

            rate = (
                total / sweep_count
            ) * 100

            print(
                f"Validation Rate          : "
                f"{rate:.2f}%"
            )

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        validated = self.get_validated_sweeps(df)

        print("\nFirst 20 Validated Sweeps\n")

        if validated.empty:

            print("No Validated Sweeps Found.")
            return

        print(

            validated[
                [
                    "index",
                    "time",
                    "validated_type"
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
    from analysis.liquidity_sweep_detector_v2 import (
        LiquiditySweepDetector
    )
    from analysis.choch_detector_v3 import CHOCHDetector

    print("=" * 60)
    print("QUANTEDGE VALIDATED SWEEP DETECTOR V2")
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
    # Liquidity Sweep Detector
    # ---------------------------------------------

    sweep = LiquiditySweepDetector()

    df = sweep.run(df)

    # ---------------------------------------------
    # CHOCH Detector
    # ---------------------------------------------

    choch = CHOCHDetector()

    df = choch.run(df)

    # ---------------------------------------------
    # Validated Sweep Detector
    # ---------------------------------------------

    validated = ValidatedSweepDetector()

    df = validated.run(
        df,
        save_output=True
    )

    validated.report(df)

    validated.summary(df)

    print("\nValidation Complete")

    print("=" * 60)