"""
=========================================================
QuantEdge V2
FVG Detector V2
=========================================================

Detects Bullish and Bearish
Fair Value Gaps (FVG)

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class FVGDetector:

    def __init__(self):

        self.min_gap = 0.0005

        self.bullish_fvg = 0
        self.bearish_fvg = 0

    # =====================================================
    # Detect FVG
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

        df["fvg"] = False
        df["fvg_type"] = None
        df["fvg_top"] = None
        df["fvg_bottom"] = None
        df["fvg_gap"] = None

        fvg_list = []

        self.bullish_fvg = 0
        self.bearish_fvg = 0

        print()
        print("=" * 60)
        print("FVG DETECTOR V2")
        print("=" * 60)

        # -----------------------------------------
        # Detect FVG
        # -----------------------------------------
        for i in range(2, len(df)):

            c1 = df.iloc[i - 2]
            c2 = df.iloc[i - 1]
            c3 = df.iloc[i]

            # =====================================
            # Bullish FVG
            # =====================================

            bullish_gap = (
                c3["low"]
                - c1["high"]
            )

            if bullish_gap >= self.min_gap:

                df.loc[
                    i,
                    "fvg"
                ] = True

                df.loc[
                    i,
                    "fvg_type"
                ] = "BULLISH_FVG"

                df.loc[
                    i,
                    "fvg_top"
                ] = round(
                    c3["low"],
                    5
                )

                df.loc[
                    i,
                    "fvg_bottom"
                ] = round(
                    c1["high"],
                    5
                )

                df.loc[
                    i,
                    "fvg_gap"
                ] = round(
                    bullish_gap,
                    5
                )

                fvg_list.append({

                    "time": c3["time"],
                    "type": "BULLISH_FVG",
                    "top": round(
                        c3["low"],
                        5
                    ),
                    "bottom": round(
                        c1["high"],
                        5
                    ),
                    "gap_size": round(
                        bullish_gap,
                        5
                    )

                })

                self.bullish_fvg += 1

            # =====================================
            # Bearish FVG
            # =====================================

            bearish_gap = (
                c1["low"]
                - c3["high"]
            )

            if bearish_gap >= self.min_gap:

                df.loc[
                    i,
                    "fvg"
                ] = True

                df.loc[
                    i,
                    "fvg_type"
                ] = "BEARISH_FVG"

                df.loc[
                    i,
                    "fvg_top"
                ] = round(
                    c1["low"],
                    5
                )

                df.loc[
                    i,
                    "fvg_bottom"
                ] = round(
                    c3["high"],
                    5
                )

                df.loc[
                    i,
                    "fvg_gap"
                ] = round(
                    bearish_gap,
                    5
                )

                fvg_list.append({

                    "time": c3["time"],
                    "type": "BEARISH_FVG",
                    "top": round(
                        c1["low"],
                        5
                    ),
                    "bottom": round(
                        c3["high"],
                        5
                    ),
                    "gap_size": round(
                        bearish_gap,
                        5
                    )

                })

                self.bearish_fvg += 1

        # -----------------------------------------
        # Remove Duplicates
        # -----------------------------------------

        fvg_df = pd.DataFrame(
            fvg_list
        )

        if not fvg_df.empty:

            fvg_df = (

                fvg_df
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

            fvg_df.to_csv(

                f"{OUTPUT_FOLDER}/fvg_v2.csv",

                index=False

            )

        return df
        # =====================================================
    # Get FVGs
    # =====================================================

    def get_fvg(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        fvg = df[
            df["fvg"] == True
        ].copy()

        return fvg.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        fvg = self.get_fvg(df)

        total = (
            self.bullish_fvg
            + self.bearish_fvg
        )

        print()

        print("=" * 60)
        print("FVG DETECTOR V2 REPORT")
        print("=" * 60)

        print(
            f"Bullish FVG : "
            f"{self.bullish_fvg:,}"
        )

        print(
            f"Bearish FVG : "
            f"{self.bearish_fvg:,}"
        )

        print(
            f"Total FVG   : "
            f"{total:,}"
        )

        if not fvg.empty:

            print(
                f"Largest Gap : "
                f"{fvg['fvg_gap'].max():.5f}"
            )

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        fvg = self.get_fvg(df)

        print("\nFirst 20 FVGs\n")

        if fvg.empty:

            print("No FVGs Found.")
            return

        print(

            fvg[
                [
                    "index",
                    "time",
                    "fvg_type",
                    "fvg_top",
                    "fvg_bottom",
                    "fvg_gap"
                ]
            ].head(20)

        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from config import HISTORICAL_FILE

    print("=" * 60)
    print("QUANTEDGE FVG DETECTOR V2")
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
    # FVG Detector
    # ---------------------------------------------

    detector = FVGDetector()

    df = detector.run(
        df,
        save_output=True
    )

    detector.report(df)

    detector.summary(df)

    print("\nValidation Complete")

    print("=" * 60)