"""
=========================================================
QuantEdge V2
Swing Detector V3
=========================================================

3 Left + 3 Right Swing Detection

Architecture:
    Input  : OHLC DataFrame
    Output : Same DataFrame enriched with swing metadata

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class SwingDetector:

    def __init__(self):

        self.swing_highs = []
        self.swing_lows = []

    # =====================================================
    # Detect Swings
    # =====================================================

    def run(
        self,
        df: pd.DataFrame,
        save_output: bool = False
    ) -> pd.DataFrame:

        df = df.copy()

        self.swing_highs.clear()
        self.swing_lows.clear()

        # -------------------------------------------------
        # Initialize Columns
        # -------------------------------------------------

        df["swing_high"] = False
        df["swing_low"] = False

        df["swing_type"] = None
        df["swing_price"] = None

        # -------------------------------------------------
        # Swing Detection
        # -------------------------------------------------

        for i in range(3, len(df) - 3):

            # =============================================
            # Swing High
            # =============================================

            if (

                df.loc[i, "high"] > df.loc[i - 1, "high"]
                and df.loc[i, "high"] > df.loc[i - 2, "high"]
                and df.loc[i, "high"] > df.loc[i - 3, "high"]

                and df.loc[i, "high"] > df.loc[i + 1, "high"]
                and df.loc[i, "high"] > df.loc[i + 2, "high"]
                and df.loc[i, "high"] > df.loc[i + 3, "high"]

            ):

                self.swing_highs.append(i)

                df.loc[i, "swing_high"] = True
                df.loc[i, "swing_type"] = "SH"
                df.loc[i, "swing_price"] = df.loc[i, "high"]

            # =============================================
            # Swing Low
            # =============================================

            if (

                df.loc[i, "low"] < df.loc[i - 1, "low"]
                and df.loc[i, "low"] < df.loc[i - 2, "low"]
                and df.loc[i, "low"] < df.loc[i - 3, "low"]

                and df.loc[i, "low"] < df.loc[i + 1, "low"]
                and df.loc[i, "low"] < df.loc[i + 2, "low"]
                and df.loc[i, "low"] < df.loc[i + 3, "low"]

            ):

                self.swing_lows.append(i)

                df.loc[i, "swing_low"] = True
                df.loc[i, "swing_type"] = "SL"
                df.loc[i, "swing_price"] = df.loc[i, "low"]

        # -------------------------------------------------
        # Optional CSV Export
        # -------------------------------------------------

        if save_output:

            Path(OUTPUT_FOLDER).mkdir(
                exist_ok=True
            )

            df.to_csv(
                f"{OUTPUT_FOLDER}/swings_v3.csv",
                index=False
            )

        return df

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        total_swings = (
            len(self.swing_highs)
            + len(self.swing_lows)
        )

        density = (
            total_swings / len(df)
        ) * 100

        print()

        print("=" * 60)
        print("SWING DETECTOR V3 REPORT")
        print("=" * 60)

        print(f"Total Candles : {len(df):,}")
        print(f"Swing Highs   : {len(self.swing_highs):,}")
        print(f"Swing Lows    : {len(self.swing_lows):,}")
        print(f"Total Swings  : {total_swings:,}")
        print(f"Swing Density : {density:.2f}%")

        print("=" * 60)
            # =====================================================
    # Get Swing Points
    # =====================================================

    def get_swings(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Returns only swing candles.
        This DataFrame will be used by
        Market Structure V4.
        """

        swings = df[
            df["swing_type"].notna()
        ].copy()

        return swings.reset_index(drop=False)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        swings = self.get_swings(df)

        print("\nFirst 10 Swings\n")

        print(
            swings[
                [
                    "index",
                    "time",
                    "swing_type",
                    "swing_price"
                ]
            ].head(10)
        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from config_backtest import HISTORICAL_FILE

    df = pd.read_csv(HISTORICAL_FILE)

    detector = SwingDetector()

    df = detector.run(
        df,
        save_output=True
    )

    detector.report(df)

    detector.summary(df)

    print("\nValidation Complete")