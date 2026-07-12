"""
=========================================================
QuantEdge V2
Signal Flow Report
=========================================================

Displays the number of events
generated at each stage of
the QuantEdge pipeline.

Author : QuantEdge
"""

import pandas as pd


class SignalFlowReport:

    def __init__(self):

        self.report_data = {}

    # =====================================================
    # Generate Report
    # =====================================================

    def run(
        self,
        df: pd.DataFrame
    ):

        self.report_data = {

            "Validated Sweeps": len(
                df[
                    df["validated_sweep"] == True
                ]
            ),

            "Order Blocks": len(
                df[
                    df["order_block"] == True
                ]
            ),

            "FVGs": len(
                df[
                    df["fvg"] == True
                ]
            ),

            "Signals": len(
                df[
                    df["signal"] == True
                ]
            )

        }

        return self.report_data
        # =====================================================
    # Report
    # =====================================================

    def report(self):

        print()

        print("=" * 60)
        print("QUANTEDGE FLOW REPORT")
        print("=" * 60)

        for name, count in self.report_data.items():

            print(f"{name:<20}: {count:,}")

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(self):

        total_events = sum(
            self.report_data.values()
        )

        print()
        print(
            f"Total Pipeline Events : "
            f"{total_events:,}"
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
    from analysis.liquidity_sweep_detector_v2 import (
        LiquiditySweepDetector
    )
    from analysis.validated_sweeps_v2 import (
        ValidatedSweepDetector
    )
    from analysis.order_block_detector_v1 import (
        OrderBlockDetector
    )
    from analysis.fvg_detector_v2 import (
        FVGDetector
    )
    from analysis.signal_generator_v3 import (
        SignalGenerator
    )

    print("=" * 60)
    print("QUANTEDGE SIGNAL FLOW REPORT")
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
    # Complete Analysis Pipeline
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
    df = SignalGenerator().run(df)

    # ---------------------------------------------
    # Signal Flow Report
    # ---------------------------------------------

    flow = SignalFlowReport()

    flow.run(df)

    flow.report()

    flow.summary()

    print("\nValidation Complete")

    print("=" * 60)