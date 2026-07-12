"""
=========================================================
QuantEdge V2
Signal Generator V3
=========================================================

Generates BUY and SELL signals
using

Validated Sweep
+
Order Block
+
Fair Value Gap

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class SignalGenerator:

    def __init__(self):

        self.buy_signals = 0
        self.sell_signals = 0

    # =====================================================
    # Generate Signals
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

        df["signal"] = False
        df["direction"] = None
        df["entry"] = None
        df["sl"] = None
        df["tp"] = None
        df["rr"] = None

        validated = df[
            df["validated_sweep"] == True
        ].copy()

        validated = validated.reset_index()

        order_blocks = df[
            df["order_block"] == True
        ].copy()

        fvgs = df[
            df["fvg"] == True
        ].copy()

        signals = []

        self.buy_signals = 0
        self.sell_signals = 0

        print()
        print("=" * 60)
        print("SIGNAL GENERATOR V3")
        print("=" * 60)

        # -----------------------------------------
        # Generate Signals
        # -----------------------------------------
        for _, sweep in validated.iterrows():

            signal_time = sweep["time"]
            sweep_type = sweep["validated_type"]

            # =====================================
            # BUY SIGNAL
            # =====================================

            if sweep_type == "SSL_SWEEP":

                matching_obs = order_blocks[

                    (order_blocks["ob_type"] == "BULLISH_OB")

                    &

                    (order_blocks["time"] <= signal_time)

                ].copy()

                if matching_obs.empty:
                    continue

                matching_obs["distance"] = (
                    signal_time -
                    matching_obs["time"]
                )

                matching_obs = matching_obs[

                    matching_obs["distance"]
                    <= pd.Timedelta(days=7)

                ]

                if matching_obs.empty:
                    continue

                ob = matching_obs.sort_values(
                    by="distance"
                ).iloc[0]

                matching_fvg = fvgs[

                    (fvgs["fvg_type"] == "BULLISH_FVG")

                    &

                    (fvgs["time"] >= ob["time"])

                    &

                    (
                        fvgs["time"]
                        <=
                        ob["time"] +
                        pd.Timedelta(days=7)
                    )

                ]

                if matching_fvg.empty:
                    continue

                entry = ob["ob_high"]
                sl = ob["ob_low"]

                risk = entry - sl

                if risk <= 0:
                    continue

                tp = entry + (risk * 3)

                candle = int(ob.name)

                df.loc[candle, "signal"] = True
                df.loc[candle, "direction"] = "BUY"
                df.loc[candle, "entry"] = round(entry, 5)
                df.loc[candle, "sl"] = round(sl, 5)
                df.loc[candle, "tp"] = round(tp, 5)
                df.loc[candle, "rr"] = 3

                signals.append({

                    "signal_time": ob["time"],
                    "direction": "BUY",
                    "entry": round(entry, 5),
                    "sl": round(sl, 5),
                    "tp": round(tp, 5),
                    "risk": round(risk, 5),
                    "reward": round(risk * 3, 5),
                    "rr": 3

                })

                self.buy_signals += 1

            # =====================================
            # SELL SIGNAL
            # =====================================

            elif sweep_type == "BSL_SWEEP":

                matching_obs = order_blocks[

                    (order_blocks["ob_type"] == "BEARISH_OB")

                    &

                    (order_blocks["time"] <= signal_time)

                ].copy()

                if matching_obs.empty:
                    continue

                matching_obs["distance"] = (
                    signal_time -
                    matching_obs["time"]
                )

                matching_obs = matching_obs[

                    matching_obs["distance"]
                    <= pd.Timedelta(days=7)

                ]

                if matching_obs.empty:
                    continue

                ob = matching_obs.sort_values(
                    by="distance"
                ).iloc[0]

                matching_fvg = fvgs[

                    (fvgs["fvg_type"] == "BEARISH_FVG")

                    &

                    (fvgs["time"] >= ob["time"])

                    &

                    (
                        fvgs["time"]
                        <=
                        ob["time"] +
                        pd.Timedelta(days=7)
                    )

                ]

                if matching_fvg.empty:
                    continue

                entry = ob["ob_low"]
                sl = ob["ob_high"]

                risk = sl - entry

                if risk <= 0:
                    continue

                tp = entry - (risk * 3)

                candle = int(ob.name)

                df.loc[candle, "signal"] = True
                df.loc[candle, "direction"] = "SELL"
                df.loc[candle, "entry"] = round(entry, 5)
                df.loc[candle, "sl"] = round(sl, 5)
                df.loc[candle, "tp"] = round(tp, 5)
                df.loc[candle, "rr"] = 3

                signals.append({

                    "signal_time": ob["time"],
                    "direction": "SELL",
                    "entry": round(entry, 5),
                    "sl": round(sl, 5),
                    "tp": round(tp, 5),
                    "risk": round(risk, 5),
                    "reward": round(risk * 3, 5),
                    "rr": 3

                })

                self.sell_signals += 1

        # -----------------------------------------
        # Remove Duplicates
        # -----------------------------------------

        signals_df = pd.DataFrame(
            signals
        )

        if not signals_df.empty:

            signals_df = (

                signals_df
                .drop_duplicates()
                .sort_values(
                    by="signal_time"
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

            signals_df.to_csv(

                f"{OUTPUT_FOLDER}/signals_v3.csv",

                index=False

            )

        return df
        # =====================================================
    # Get Signals
    # =====================================================

    def get_signals(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        signals = df[
            df["signal"] == True
        ].copy()

        return signals.reset_index(
            drop=False
        )

    # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        df: pd.DataFrame
    ):

        signals = self.get_signals(df)

        total = (
            self.buy_signals
            + self.sell_signals
        )

        validated = len(
            df[
                df["validated_sweep"] == True
            ]
        )

        print()

        print("=" * 60)
        print("SIGNAL GENERATOR V3 REPORT")
        print("=" * 60)

        print(f"BUY Signals  : {self.buy_signals:,}")
        print(f"SELL Signals : {self.sell_signals:,}")
        print(f"Total Signals: {total:,}")

        if validated > 0:

            print(
                f"Signal Rate  : "
                f"{(total / validated) * 100:.2f}%"
            )

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        df: pd.DataFrame
    ):

        signals = self.get_signals(df)

        print("\nFirst 20 Signals\n")

        if signals.empty:

            print("No Signals Found.")
            return

        print(

            signals[
                [
                    "index",
                    "time",
                    "direction",
                    "entry",
                    "sl",
                    "tp",
                    "rr"
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
    from analysis.bos_detector_v4 import BOSDetector
    from analysis.choch_detector_v3 import CHOCHDetector
    from analysis.liquidity_detector_v2 import LiquidityDetector
    from analysis.liquidity_sweep_detector_v2 import LiquiditySweepDetector
    from analysis.validated_sweeps_v2 import (
        ValidatedSweepDetector
    )
    from analysis.order_block_detector_v1 import (
        OrderBlockDetector
    )
    from analysis.fvg_detector_v2 import (
        FVGDetector
    )

    print("=" * 60)
    print("QUANTEDGE SIGNAL GENERATOR V3")
    print("=" * 60)

    # ---------------------------------------------
    # Load Historical Data
    # ---------------------------------------------

    df = pd.read_csv(HISTORICAL_FILE)

    print(f"Candles Loaded : {len(df):,}")

    # ---------------------------------------------
    # Complete Pipeline
    # ---------------------------------------------

    df = SwingDetector().run(df)

    df = MarketStructure().run(df)

    df = BOSDetector().run(df)

    df = CHOCHDetector().run(df)

    df = LiquidityDetector().run(df)

    df = LiquiditySweepDetector().run(df)

    df = ValidatedSweepDetector().run(df)

    df = OrderBlockDetector().run(df)

    df = FVGDetector().run(df)

    generator = SignalGenerator()

    df = generator.run(
        df,
        save_output=True
    )

    generator.report(df)

    generator.summary(df)

    print("\nValidation Complete")

    print("=" * 60)