"""
=========================================================
QuantEdge V2
CHOCH Detector V3
=========================================================

Detects Change of Character (CHOCH)

Input:
    DataFrame from Market Structure

Output:
    Same DataFrame enriched with CHOCH information

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class CHOCHDetector:

    def __init__(self):

        self.lookahead = 500

        self.bullish_choch = 0
        self.bearish_choch = 0

    # =====================================================
    # Detect CHOCH
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

        df["choch"] = False
        df["choch_type"] = None
        df["choch_level"] = None

        # ---------------------------------------------
        # Structure Data
        # ---------------------------------------------

        structure = df[
            df["structure"].notna()
        ].copy()

        structure = structure.reset_index()

        structure.rename(
            columns={
                "index": "candle_index"
            },
            inplace=True
        )

        close_prices = df["close"].values
        times = df["time"].values

        trend = None

        protected_HL = None
        protected_LH = None

        choch_events = []

        self.bullish_choch = 0
        self.bearish_choch = 0

        # ---------------------------------------------
        # Initial Trend
        # ---------------------------------------------

        for _, row in structure.iterrows():

            label = row["structure"]

            if label == "HH":

                trend = "bullish"
                break

            elif label == "LL":

                trend = "bearish"
                break

        print(f"Initial Trend : {trend}")
                # ---------------------------------------------
        # Main CHOCH Detection Loop
        # ---------------------------------------------

        for _, row in structure.iterrows():

            label = row["structure"]
            idx = int(row["candle_index"])

            # -----------------------------------------
            # Store Protected Levels
            # -----------------------------------------

            if label == "HL":

                protected_HL = row

            elif label == "LH":

                protected_LH = row

            # =========================================
            # Bullish → Bearish CHOCH
            # =========================================

            if trend == "bullish":

                if protected_HL is not None:

                    level = protected_HL["swing_price"]

                    for j in range(
                        idx + 1,
                        min(
                            idx + self.lookahead,
                            len(close_prices)
                        )
                    ):

                        if close_prices[j] < level:

                            df.loc[j, "choch"] = True
                            df.loc[j, "choch_type"] = "BEARISH_CHOCH"
                            df.loc[j, "choch_level"] = level

                            choch_events.append({

                                "time": times[j],
                                "type": "BEARISH_CHOCH",
                                "price": level

                            })

                            self.bearish_choch += 1

                            trend = "bearish"

                            protected_HL = None
                            protected_LH = None

                            break

            # =========================================
            # Bearish → Bullish CHOCH
            # =========================================

            elif trend == "bearish":

                if protected_LH is not None:

                    level = protected_LH["swing_price"]

                    for j in range(
                        idx + 1,
                        min(
                            idx + self.lookahead,
                            len(close_prices)
                        )
                    ):

                        if close_prices[j] > level:

                            df.loc[j, "choch"] = True
                            df.loc[j, "choch_type"] = "BULLISH_CHOCH"
                            df.loc[j, "choch_level"] = level

                            choch_events.append({

                                "time": times[j],
                                "type": "BULLISH_CHOCH",
                                "price": level

                            })

                            self.bullish_choch += 1

                            trend = "bullish"

                            protected_HL = None
                            protected_LH = None

                            break

        # ---------------------------------------------
        # Optional CSV Export
        # ---------------------------------------------

        if save_output:

            Path(
                OUTPUT_FOLDER
            ).mkdir(
                exist_ok=True
            )

            choch_df = pd.DataFrame(
                choch_events
            )

            choch_df.to_csv(
                f"{OUTPUT_FOLDER}/choch_events.csv",
                index=False
            )

        return df
        # =====================================================
    # Get CHOCH Events
    # =====================================================

    def get_choch(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        choch = df[
            df["choch"] == True
        ].copy()

        return choch.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        choch = self.get_choch(df)

        total = (
            self.bullish_choch
            + self.bearish_choch
        )

        structure_count = len(
            df[df["structure"].notna()]
        )

        print()

        print("=" * 60)
        print("CHOCH DETECTOR V3 REPORT")
        print("=" * 60)

        print(f"Structure Points : {structure_count:,}")
        print(f"Bullish CHOCH    : {self.bullish_choch:,}")
        print(f"Bearish CHOCH    : {self.bearish_choch:,}")
        print(f"Total CHOCH      : {total:,}")

        if structure_count > 0:

            ratio = (
                total / structure_count
            ) * 100

            print(f"CHOCH Ratio      : {ratio:.2f}%")

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        choch = self.get_choch(df)

        print("\nFirst 20 CHOCH Events\n")

        if choch.empty:

            print("No CHOCH detected.")
            return

        print(

            choch[
                [
                    "index",
                    "time",
                    "choch_type",
                    "choch_level"
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
    print("QUANTEDGE CHOCH DETECTOR V3")
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
    # CHOCH Detector
    # ---------------------------------------------

    choch = CHOCHDetector()

    df = choch.run(
        df,
        save_output=True
    )

    choch.report(df)

    choch.summary(df)

    print("\nValidation Complete")

    print("=" * 60)