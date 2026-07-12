"""
=========================================================
QuantEdge V2
BOS Detector V4
=========================================================

Detects Break of Structure (BOS)

Input:
    DataFrame from MarketStructure

Output:
    Same DataFrame enriched with BOS information

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class BOSDetector:

    def __init__(self):

        self.bullish_bos = 0
        self.bearish_bos = 0

    # =====================================================
    # Detect BOS
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

        df["bos"] = False
        df["bos_type"] = None
        df["bos_level"] = None

        # -----------------------------------------
        # Structure Points
        # -----------------------------------------

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

        bos_events = []

        self.bullish_bos = 0
        self.bearish_bos = 0
                # -----------------------------------------
        # Bullish & Bearish BOS Detection
        # -----------------------------------------

        for _, swing in structure.iterrows():

            # =====================================
            # Bullish BOS
            # =====================================

            if swing["structure"] == "HH":

                level = swing["swing_price"]

                for j in range(
                    swing["candle_index"] + 1,
                    len(df)
                ):

                    if df.loc[j, "close"] > level:

                        df.loc[j, "bos"] = True
                        df.loc[j, "bos_type"] = "Bullish BOS"
                        df.loc[j, "bos_level"] = level

                        bos_events.append({
                            "time": df.loc[j, "time"],
                            "type": "Bullish BOS",
                            "level": level
                        })

                        self.bullish_bos += 1

                        break

            # =====================================
            # Bearish BOS
            # =====================================

            elif swing["structure"] == "LL":

                level = swing["swing_price"]

                for j in range(
                    swing["candle_index"] + 1,
                    len(df)
                ):

                    if df.loc[j, "close"] < level:

                        df.loc[j, "bos"] = True
                        df.loc[j, "bos_type"] = "Bearish BOS"
                        df.loc[j, "bos_level"] = level

                        bos_events.append({
                            "time": df.loc[j, "time"],
                            "type": "Bearish BOS",
                            "level": level
                        })

                        self.bearish_bos += 1

                        break

        # -----------------------------------------
        # Optional CSV Export
        # -----------------------------------------

        if save_output:

            Path(
                OUTPUT_FOLDER
            ).mkdir(
                exist_ok=True
            )

            bos_df = pd.DataFrame(
                bos_events
            )

            bos_df.to_csv(
                f"{OUTPUT_FOLDER}/bos_events_v4.csv",
                index=False
            )

        return df
        # =====================================================
    # Get BOS Events
    # =====================================================

    def get_bos(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        bos = df[
            df["bos"] == True
        ].copy()

        return bos.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        bos = self.get_bos(df)

        total = (
            self.bullish_bos
            + self.bearish_bos
        )

        print()

        print("=" * 60)
        print("BOS DETECTOR V4 REPORT")
        print("=" * 60)

        print(f"Total Structure : {len(df[df['structure'].notna()]):,}")
        print(f"Bullish BOS     : {self.bullish_bos:,}")
        print(f"Bearish BOS     : {self.bearish_bos:,}")
        print(f"Total BOS       : {total:,}")

        if len(df[df["structure"].notna()]) > 0:

            ratio = (
                total
                /
                len(df[df["structure"].notna()])
            ) * 100

            print(f"BOS Ratio       : {ratio:.2f}%")

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        bos = self.get_bos(df)

        print("\nFirst 20 BOS Events\n")

        if bos.empty:

            print("No BOS detected.")
            return

        print(
            bos[
                [
                    "index",
                    "time",
                    "bos_type",
                    "bos_level"
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
    print("QUANTEDGE BOS DETECTOR V4")
    print("=" * 60)

    # ---------------------------------------------
    # Load Historical Data
    # ---------------------------------------------

    df = pd.read_csv(HISTORICAL_FILE)

    print(f"Candles Loaded : {len(df):,}")

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
    # BOS Detector
    # ---------------------------------------------

    bos = BOSDetector()

    df = bos.run(
        df,
        save_output=True
    )

    bos.report(df)

    bos.summary(df)

    print("\nValidation Complete")

    print("=" * 60)