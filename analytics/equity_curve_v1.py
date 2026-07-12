"""
=========================================================
QuantEdge V2
Equity Curve
=========================================================

Generates the equity curve
from backtest results.

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class EquityCurve:

    def __init__(

        self,

        starting_balance=10000,

        risk_per_trade=100

    ):

        self.starting_balance = starting_balance
        self.risk_per_trade = risk_per_trade

    # =====================================================
    # Generate Equity Curve
    # =====================================================

    def run(

        self,

        trades: pd.DataFrame,

        save_output=False

    ) -> pd.DataFrame:

        trades = trades.copy()

        equity = self.starting_balance

        curve = []

        for i, row in trades.iterrows():

            equity += (

                row["rr"]

                * self.risk_per_trade

            )

            curve.append({

                "trade_no": i + 1,

                "equity": round(
                    equity,
                    2
                )

            })

        curve_df = pd.DataFrame(
            curve
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

            curve_df.to_csv(

                f"{OUTPUT_FOLDER}/equity_curve.csv",

                index=False

            )

        return curve_df
        # =====================================================
    # Report
    # =====================================================

    def report(
        self,
        curve_df: pd.DataFrame
    ):

        print()

        print("=" * 60)
        print("EQUITY CURVE REPORT")
        print("=" * 60)

        print(
            f"Starting Balance : "
            f"{self.starting_balance:,.2f}"
        )

        if not curve_df.empty:

            print(
                f"Ending Balance   : "
                f"{curve_df.iloc[-1]['equity']:,.2f}"
            )

            print(
                f"Total Trades     : "
                f"{len(curve_df):,}"
            )

        print("=" * 60)

    # =====================================================
    # Summary
    # =====================================================

    def summary(
        self,
        curve_df: pd.DataFrame
    ):

        print("\nLast 10 Equity Values\n")

        if curve_df.empty:

            print("No Trades Found.")
            return

        print(
            curve_df.tail(10)
        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from config import OUTPUT_FOLDER

    trades = pd.read_csv(
        f"{OUTPUT_FOLDER}/backtest_results_v1.csv"
    )

    print("=" * 60)
    print("QUANTEDGE EQUITY CURVE")
    print("=" * 60)

    print(
        f"Trades Loaded : {len(trades):,}"
    )

    curve = EquityCurve(

        starting_balance=10000,

        risk_per_trade=100

    )

    curve_df = curve.run(

        trades,

        save_output=True

    )

    curve.report(
        curve_df
    )

    curve.summary(
        curve_df
    )

    print("\nValidation Complete")

    print("=" * 60)