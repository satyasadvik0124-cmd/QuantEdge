"""
=========================================================
QuantEdge V2
Order Block Detector V1
=========================================================

Detects Bullish and Bearish
Order Blocks after
Validated Liquidity Sweeps.

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class OrderBlockDetector:

    def __init__(self):

        self.lookback = 20

        self.bullish_ob = 0
        self.bearish_ob = 0

    # =====================================================
    # Detect Order Blocks
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

        df["order_block"] = False
        df["ob_type"] = None
        df["ob_high"] = None
        df["ob_low"] = None

        validated = df[
            df["validated_sweep"] == True
        ].copy()

        validated = validated.reset_index()

        validated.rename(
            columns={
                "index": "candle_index"
            },
            inplace=True
        )

        order_blocks = []

        self.bullish_ob = 0
        self.bearish_ob = 0

        print()
        print("=" * 60)
        print("ORDER BLOCK DETECTOR V1")
        print("=" * 60)

        # -----------------------------------------
        # Detect Order Blocks
        # -----------------------------------------
        for _, sweep in validated.iterrows():

            choch_idx = int(
                sweep["candle_index"]
            )

            sweep_type = sweep["validated_type"]

            # -------------------------------------
            # Debug (First 5 Only)
            # -------------------------------------

            if len(order_blocks) < 5:

                print(

                    f"CHOCH Index={choch_idx} | "
                    f"TYPE={sweep_type}"

                )

            # =====================================
            # SSL Sweep
            # → Bullish Order Block
            # =====================================

            if sweep_type == "SSL_SWEEP":

                for i in range(

                    choch_idx - 1,

                    max(
                        0,
                        choch_idx - self.lookback
                    ),

                    -1

                ):

                    candle = df.iloc[i]

                    if candle["close"] < candle["open"]:

                        df.loc[
                            i,
                            "order_block"
                        ] = True

                        df.loc[
                            i,
                            "ob_type"
                        ] = "BULLISH_OB"

                        df.loc[
                            i,
                            "ob_high"
                        ] = candle["high"]

                        df.loc[
                            i,
                            "ob_low"
                        ] = candle["low"]

                        order_blocks.append({

                            "time": candle["time"],
                            "type": "BULLISH_OB",
                            "high": candle["high"],
                            "low": candle["low"]

                        })

                        self.bullish_ob += 1

                        break

            # =====================================
            # BSL Sweep
            # → Bearish Order Block
            # =====================================

            elif sweep_type == "BSL_SWEEP":

                for i in range(

                    choch_idx - 1,

                    max(
                        0,
                        choch_idx - self.lookback
                    ),

                    -1

                ):

                    candle = df.iloc[i]

                    if candle["close"] > candle["open"]:

                        df.loc[
                            i,
                            "order_block"
                        ] = True

                        df.loc[
                            i,
                            "ob_type"
                        ] = "BEARISH_OB"

                        df.loc[
                            i,
                            "ob_high"
                        ] = candle["high"]

                        df.loc[
                            i,
                            "ob_low"
                        ] = candle["low"]

                        order_blocks.append({

                            "time": candle["time"],
                            "type": "BEARISH_OB",
                            "high": candle["high"],
                            "low": candle["low"]

                        })

                        self.bearish_ob += 1

                        break

        # -----------------------------------------
        # Remove Duplicates
        # -----------------------------------------

        ob_df = pd.DataFrame(
            order_blocks
        )

        if not ob_df.empty:

            ob_df = (

                ob_df
                .drop_duplicates()
                .sort_values(
                    by="time"
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

            ob_df.to_csv(

                f"{OUTPUT_FOLDER}/order_blocks_v1.csv",

                index=False

            )

        return df
        # =====================================================
    # Get Order Blocks
    # =====================================================

    def get_order_blocks(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        order_blocks = df[
            df["order_block"] == True
        ].copy()

        return order_blocks.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        order_blocks = self.get_order_blocks(df)

        total = (
            self.bullish_ob
            + self.bearish_ob
        )

        validated_count = len(
            df[df["validated_sweep"] == True]
        )

        print()

        print("=" * 60)
        print("ORDER BLOCK DETECTOR V1 REPORT")
        print("=" * 60)

        print(
            f"Bullish Order Blocks : "
            f"{self.bullish_ob:,}"
        )

        print(
            f"Bearish Order Blocks : "
            f"{self.bearish_ob:,}"
        )

        print(
            f"Total Order Blocks   : "
            f"{total:,}"
        )

        if validated_count > 0:

            rate = (
                total / validated_count
            ) * 100

            print(
                f"OB Conversion Rate   : "
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

        order_blocks = self.get_order_blocks(df)

        print("\nFirst 20 Order Blocks\n")

        if order_blocks.empty:

            print("No Order Blocks Found.")
            return

        print(

            order_blocks[
                [
                    "index",
                    "time",
                    "ob_type",
                    "ob_high",
                    "ob_low"
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
    from analysis.validated_sweeps_v2 import (
        ValidatedSweepDetector
    )

    print("=" * 60)
    print("QUANTEDGE ORDER BLOCK DETECTOR V1")
    print("=" * 60)

    # ---------------------------------------------
    # Load Historical Data
    # ---------------------------------------------

    df = pd.read_csv(HISTORICAL_FILE)

    print(
        f"Candles Loaded : {len(df):,}"
    )

    # ---------------------------------------------
    # Run Pipeline
    # ---------------------------------------------

    df = SwingDetector().run(df)

    df = MarketStructure().run(df)

    df = LiquidityDetector().run(df)

    df = LiquiditySweepDetector().run(df)

    df = CHOCHDetector().run(df)

    df = ValidatedSweepDetector().run(df)

    detector = OrderBlockDetector()

    df = detector.run(
        df,
        save_output=True
    )

    detector.report(df)

    detector.summary(df)

    print("\nValidation Complete")

    print("=" * 60)