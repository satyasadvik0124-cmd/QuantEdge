"""
=========================================================
QuantEdge V2
Market Structure V4
=========================================================

Converts swing points into market structure
(HH / HL / LH / LL)

Input:
    SwingDetector Output DataFrame

Output:
    Same DataFrame enriched with
    market structure information

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER
from config_backtest import PAIR
from config_strategy import (
    FOREX_MIN_SWING_DISTANCE,
    XAU_MIN_SWING_DISTANCE
)

class MarketStructure:

    def __init__(self):
        
      if PAIR == "XAUUSD":
       MIN_DISTANCE = XAU_MIN_SWING_DISTANCE
      else:
       MIN_DISTANCE = FOREX_MIN_SWING_DISTANCE

    # =====================================================
    # Detect Market Structure
    # =====================================================

    def run(
        self,
        df: pd.DataFrame,
        save_output=False
    ) -> pd.DataFrame:

        df = df.copy()

        # ---------------------------------------------
        # Initialize Columns
        # ---------------------------------------------

        df["structure"] = None

        # ---------------------------------------------
        # Get Swing Points
        # ---------------------------------------------

        swings = df[
            df["swing_type"].notna()
        ].copy()

        swings = swings.reset_index()

        swings.rename(
            columns={
                "index": "candle_index"
            },
            inplace=True
        )

        swings = swings[
            [
                "candle_index",
                "time",
                "swing_type",
                "swing_price"
            ]
        ]

        # ---------------------------------------------
        # Sort
        # ---------------------------------------------

        swings = swings.sort_values(
            "candle_index"
        ).reset_index(drop=True)

        # ---------------------------------------------
        # Remove Consecutive Same Swings
        # ---------------------------------------------

        cleaned = []

        for _, swing in swings.iterrows():

            swing = swing.to_dict()

            if not cleaned:

                cleaned.append(swing)
                continue

            last = cleaned[-1]

            if swing["swing_type"] == last["swing_type"]:

                # -------------------------
                # Higher High
                # -------------------------

                if swing["swing_type"] == "SH":

                    if (
                        swing["swing_price"]
                        >
                        last["swing_price"]
                    ):

                        cleaned[-1] = swing

                # -------------------------
                # Lower Low
                # -------------------------

                else:

                    if (
                        swing["swing_price"]
                        <
                        last["swing_price"]
                    ):

                        cleaned[-1] = swing

            else:

                cleaned.append(swing)

        # ---------------------------------------------
        # Distance Filter
        # ---------------------------------------------

        filtered = []

        for swing in cleaned:

            if not filtered:

                filtered.append(swing)
                continue

            last = filtered[-1]

            distance = abs(
                swing["swing_price"]
                -
                last["swing_price"]
            )

            if distance >= self.min_distance:

                filtered.append(swing)
                        # ---------------------------------------------
        # Label Market Structure
        # ---------------------------------------------

        last_high = None
        last_low = None

        structure = []

        for swing in filtered:

            # -----------------------------------------
            # Swing High
            # -----------------------------------------

            if swing["swing_type"] == "SH":

                if last_high is None:

                    label = "SH"

                elif swing["swing_price"] > last_high:

                    label = "HH"

                else:

                    label = "LH"

                last_high = swing["swing_price"]

            # -----------------------------------------
            # Swing Low
            # -----------------------------------------

            else:

                if last_low is None:

                    label = "SL"

                elif swing["swing_price"] > last_low:

                    label = "HL"

                else:

                    label = "LL"

                last_low = swing["swing_price"]

            swing["structure"] = label

            structure.append(swing)

        # ---------------------------------------------
        # Write Labels Back To DataFrame
        # ---------------------------------------------

        for swing in structure:

            candle = swing["candle_index"]

            df.loc[
                candle,
                "structure"
            ] = swing["structure"]

        # ---------------------------------------------
        # Optional CSV Export
        # ---------------------------------------------

        if save_output:

            Path(
                OUTPUT_FOLDER
            ).mkdir(
                exist_ok=True
            )

            structure_df = pd.DataFrame(
                structure
            )

            structure_df.to_csv(
                f"{OUTPUT_FOLDER}/market_structure_v4.csv",
                index=False
            )

        return df

    # =====================================================
    # Get Structure Points
    # =====================================================

    def get_structure(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        structure = df[
            df["structure"].notna()
        ].copy()

        return structure.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        structure = self.get_structure(df)

        hh = len(
            structure[
                structure["structure"] == "HH"
            ]
        )

        hl = len(
            structure[
                structure["structure"] == "HL"
            ]
        )

        lh = len(
            structure[
                structure["structure"] == "LH"
            ]
        )

        ll = len(
            structure[
                structure["structure"] == "LL"
            ]
        )

        sh = len(
            structure[
                structure["structure"] == "SH"
            ]
        )

        sl = len(
            structure[
                structure["structure"] == "SL"
            ]
        )

        print()

        print("=" * 60)
        print("MARKET STRUCTURE REPORT")
        print("=" * 60)

        print(f"Initial SH      : {sh}")
        print(f"Initial SL      : {sl}")

        print()

        print(f"HH Count        : {hh}")
        print(f"HL Count        : {hl}")
        print(f"LH Count        : {lh}")
        print(f"LL Count        : {ll}")

        print()

        print(
            f"Total Structure : {len(structure)}"
        )

        print("=" * 60)

            # =====================================================
    # Get Structure Points
    # =====================================================

    def get_structure(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Returns only the market structure points.

        Output Columns
        --------------
        index
        time
        price
        type
        label
        """

        structure = df[
            df["structure"].notna()
        ].copy()

        structure = structure.reset_index()

        structure.rename(
            columns={
                "index": "index",
                "structure": "label",
                "swing_type": "type",
                "swing_price": "price"
            },
            inplace=True
        )

        structure = structure[
            [
                "index",
                "time",
                "price",
                "type",
                "label"
            ]
        ]

        return structure
            # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        structure = self.get_structure(df)

        print("\nFirst 20 Structure Points\n")

        print(
            structure[
                [
                    "index",
                    "time",
                    "structure",
                    "swing_price"
                ]
            ].head(20)
        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from config_backtest import HISTORICAL_FILE
    from analysis.swing_detector_v3 import SwingDetector

    print("=" * 60)
    print("QUANTEDGE MARKET STRUCTURE V4")
    print("=" * 60)

    # -----------------------------------------------------
    # Load Historical Data
    # -----------------------------------------------------

    df = pd.read_csv(HISTORICAL_FILE)

    print(f"Candles Loaded : {len(df):,}")

    # -----------------------------------------------------
    # Swing Detection
    # -----------------------------------------------------

    swing_detector = SwingDetector()

    df = swing_detector.run(
        df,
        save_output=False
    )

    swing_detector.report(df)

    # -----------------------------------------------------
    # Market Structure
    # -----------------------------------------------------

    structure_detector = MarketStructure()

    df = structure_detector.run(
        df,
        save_output=True
    )

    structure_detector.report(df)

    structure_detector.summary(df)

    print("\nValidation Complete")

    print("=" * 60)