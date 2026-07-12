"""
=========================================================
QuantEdge V2
Drawdown Analyzer V1
=========================================================

Calculates Maximum Drawdown
from an Equity Curve.

Author : QuantEdge
"""

import pandas as pd


class DrawdownAnalyzer:

    def __init__(self):

        self.max_drawdown = 0

    # =====================================================
    # Analyze Drawdown
    # =====================================================

    def run(
        self,
        equity_curve: pd.DataFrame
    ) -> float:

        equity_curve = equity_curve.copy()

        if equity_curve.empty:

            self.max_drawdown = 0
            return self.max_drawdown

        peak = equity_curve.iloc[0]["equity"]

        self.max_drawdown = 0

        for equity in equity_curve["equity"]:

            peak = max(
                peak,
                equity
            )

            drawdown = (
                peak - equity
            )

            self.max_drawdown = max(

                self.max_drawdown,

                drawdown

            )

        return self.max_drawdown
        # =====================================================
    # Report
    # =====================================================

    def report(self):

        print()

        print("=" * 60)
        print("DRAWDOWN ANALYZER REPORT")
        print("=" * 60)

        print(
            f"Maximum Drawdown : "
            f"${self.max_drawdown:,.2f}"
        )

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(self):

        print()

        print(
            f"Maximum Drawdown = "
            f"${self.max_drawdown:,.2f}"
        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from config import OUTPUT_FOLDER

    print("=" * 60)
    print("QUANTEDGE DRAWDOWN ANALYZER")
    print("=" * 60)

    equity_curve = pd.read_csv(

        f"{OUTPUT_FOLDER}/equity_curve.csv"

    )

    print(

        f"Equity Points Loaded : "
        f"{len(equity_curve):,}"

    )

    analyzer = DrawdownAnalyzer()

    analyzer.run(
        equity_curve
    )

    analyzer.report()

    analyzer.summary()

    print("\nValidation Complete")

    print("=" * 60)