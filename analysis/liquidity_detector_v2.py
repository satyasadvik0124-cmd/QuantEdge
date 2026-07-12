"""
=========================================================
QuantEdge V2
Liquidity Detector V2
=========================================================

Detects Equal Highs (EQH)
and Equal Lows (EQL)

Input:
    DataFrame from Market Structure

Output:
    Same DataFrame enriched with
    liquidity information

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import (
    PAIR,
    OUTPUT_FOLDER
)

from analysis.market_structure_v4 import (
    MarketStructure
)


class LiquidityDetector:

    def __init__(self):

        if PAIR == "XAUUSD":
            self.tolerance = 2.0
        else:
            self.tolerance = 0.0002

        self.lookahead = 5

        self.eqh_count = 0
        self.eql_count = 0

    # =====================================================
    # Detect Liquidity
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

        df["liquidity"] = False
        df["liquidity_type"] = None
        df["liquidity_price"] = None

        # -----------------------------------------
        # Get Structure
        # -----------------------------------------

        structure_detector = MarketStructure()

        structure = structure_detector.get_structure(df)

        liquidity_levels = []

        self.eqh_count = 0
        self.eql_count = 0

        # -----------------------------------------
        # Equal Highs
        # -----------------------------------------

        swing_highs = (
            structure[
                structure["type"] == "SH"
            ]
            .reset_index(drop=True)
        )
        for i in range(len(swing_highs)):

            h1 = swing_highs.iloc[i]

            for j in range(
                i + 1,
                min(
                    i + self.lookahead + 1,
                    len(swing_highs)
                )
            ):

                h2 = swing_highs.iloc[j]

                if abs(
                    h1["price"] -
                    h2["price"]
                ) <= self.tolerance:

                    liquidity_price = round(
                        (
                            h1["price"] +
                            h2["price"]
                        ) / 2,
                        5
                    )

                    liquidity_levels.append({

                        "time": h2["time"],
                        "type": "EQH",
                        "price": liquidity_price

                    })

                    candle = int(h2["index"])

                    df.loc[
                        candle,
                        "liquidity"
                    ] = True

                    df.loc[
                        candle,
                        "liquidity_type"
                    ] = "EQH"

                    df.loc[
                        candle,
                        "liquidity_price"
                    ] = liquidity_price

                    self.eqh_count += 1

        # -----------------------------------------
        # Equal Lows
        # -----------------------------------------

        swing_lows = (
            structure[
                structure["type"] == "SL"
            ]
            .reset_index(drop=True)
        )

        for i in range(len(swing_lows)):

            l1 = swing_lows.iloc[i]

            for j in range(
                i + 1,
                min(
                    i + self.lookahead + 1,
                    len(swing_lows)
                )
            ):

                l2 = swing_lows.iloc[j]

                if abs(
                    l1["price"] -
                    l2["price"]
                ) <= self.tolerance:

                    liquidity_price = round(
                        (
                            l1["price"] +
                            l2["price"]
                        ) / 2,
                        5
                    )

                    liquidity_levels.append({

                        "time": l2["time"],
                        "type": "EQL",
                        "price": liquidity_price

                    })

                    candle = int(l2["index"])

                    df.loc[
                        candle,
                        "liquidity"
                    ] = True

                    df.loc[
                        candle,
                        "liquidity_type"
                    ] = "EQL"

                    df.loc[
                        candle,
                        "liquidity_price"
                    ] = liquidity_price

                    self.eql_count += 1

        # -----------------------------------------
        # Remove Duplicates
        # -----------------------------------------

        liquidity_df = pd.DataFrame(
            liquidity_levels
        )

        if not liquidity_df.empty:

            liquidity_df = (
                liquidity_df
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

            liquidity_df.to_csv(
                f"{OUTPUT_FOLDER}/liquidity_v2.csv",
                index=False
            )

        return df
        # =====================================================
    # Get Liquidity Levels
    # =====================================================

    def get_liquidity(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        liquidity = df[
            df["liquidity"] == True
        ].copy()

        return liquidity.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        liquidity = self.get_liquidity(df)

        total = (
            self.eqh_count
            + self.eql_count
        )

        print()

        print("=" * 60)
        print("LIQUIDITY DETECTOR V2 REPORT")
        print("=" * 60)

        print(f"Pair                   : {PAIR}")
        print(f"Tolerance              : {self.tolerance}")

        print()

        print(f"EQH Count              : {self.eqh_count:,}")
        print(f"EQL Count              : {self.eql_count:,}")
        print(f"Raw Liquidity Levels   : {total:,}")
        print(f"Unique Liquidity Levels: {len(liquidity):,}")

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        liquidity = self.get_liquidity(df)

        print("\nFirst 20 Liquidity Levels\n")

        if liquidity.empty:

            print("No Liquidity Levels Found.")
            return

        print(

            liquidity[
                [
                    "index",
                    "time",
                    "liquidity_type",
                    "liquidity_price"
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

    print("=" * 60)
    print("QUANTEDGE LIQUIDITY DETECTOR V2")
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

    df = liquidity.run(
        df,
        save_output=True
    )

    liquidity.report(df)

    liquidity.summary(df)

    print("\nValidation Complete")

    print("=" * 60)