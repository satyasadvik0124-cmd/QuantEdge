"""
=========================================================
QuantEdge V2
Performance Analyzer V1
=========================================================

Analyzes Backtest Performance.

Author : QuantEdge
"""

from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER


class PerformanceAnalyzer:

    def __init__(

        self,

        initial_capital=10000

    ):

        self.initial_capital = initial_capital

        self.metrics = {}

    # =====================================================
    # Analyze Performance
    # =====================================================

    def run(

        self,

        trades: pd.DataFrame,

        equity_curve: pd.DataFrame,

        save_output=False

    ):

        trades = trades.copy()

        equity_curve = equity_curve.copy()

        if trades.empty:

            raise ValueError(
                "No backtest trades found."
            )

        # =====================================
        # Detect Result Column
        # =====================================

        possible_result_cols = [

            "result",
            "Result",
            "outcome",
            "Outcome",
            "status",
            "Status"

        ]

        result_col = None

        for col in possible_result_cols:

            if col in trades.columns:

                result_col = col
                break

        if result_col is None:

            raise ValueError(
                "Result column not found."
            )

        # =====================================
        # Detect RR Column
        # =====================================

        possible_rr_cols = [

            "rr",
            "RR",
            "r_multiple",
            "reward",
            "reward_risk",
            "risk_reward",
            "pnl_r"

        ]

        rr_col = None

        for col in possible_rr_cols:

            if col in trades.columns:

                rr_col = col
                break

        if rr_col is None:

            raise ValueError(
                "RR column not found."
            )
            # =====================================
        # Basic Metrics
        # =====================================

        total_trades = len(trades)

        wins = len(

            trades[
                trades[result_col]
                .astype(str)
                .str.upper()
                .isin([
                    "WIN",
                    "TP",
                    "PROFIT"
                ])
            ]

        )

        losses = len(

            trades[
                trades[result_col]
                .astype(str)
                .str.upper()
                .isin([
                    "LOSS",
                    "SL",
                    "LOSE"
                ])
            ]

        )

        win_rate = (

            wins / total_trades * 100

            if total_trades > 0

            else 0

        )

        # =====================================
        # RR Metrics
        # =====================================

        avg_rr = trades[
            rr_col
        ].mean()

        gross_profit = (

            trades[
                trades[rr_col] > 0
            ][rr_col]

            .sum()

        )

        gross_loss = abs(

            trades[
                trades[rr_col] < 0
            ][rr_col]

            .sum()

        )

        profit_factor = (

            gross_profit / gross_loss

            if gross_loss > 0

            else float("inf")

        )

        net_r = trades[
            rr_col
        ].sum()

        # =====================================
        # Streaks
        # =====================================

        max_win_streak = 0
        max_loss_streak = 0

        current_win = 0
        current_loss = 0

        for result in trades[result_col]:

            result = str(
                result
            ).upper()

            if result in [

                "WIN",
                "TP",
                "PROFIT"

            ]:

                current_win += 1
                current_loss = 0

                max_win_streak = max(

                    max_win_streak,

                    current_win

                )

            elif result in [

                "LOSS",
                "SL",
                "LOSE"

            ]:

                current_loss += 1
                current_win = 0

                max_loss_streak = max(

                    max_loss_streak,

                    current_loss

                )

        # =====================================
        # Expectancy
        # =====================================

        expectancy = (

            net_r / total_trades

            if total_trades > 0

            else 0

        )

        # =====================================
        # Capital Metrics
        # =====================================

        final_capital = float(

            equity_curve.iloc[-1]["equity"]

        )

        net_profit = (

            final_capital

            - self.initial_capital

        )

        return_pct = (

            net_profit

            / self.initial_capital

        ) * 100

        # =====================================
        # Store Metrics
        # =====================================

        self.metrics = {

            "initial_capital": self.initial_capital,

            "final_capital": final_capital,

            "net_profit": net_profit,

            "return_pct": return_pct,

            "total_trades": total_trades,

            "wins": wins,

            "losses": losses,

            "win_rate": win_rate,

            "avg_rr": avg_rr,

            "gross_profit": gross_profit,

            "gross_loss": gross_loss,

            "profit_factor": profit_factor,

            "net_r": net_r,

            "max_win_streak": max_win_streak,

            "max_loss_streak": max_loss_streak,

            "expectancy": expectancy

        }

        # =====================================
        # Optional Report Save
        # =====================================

        if save_output:

            Path(
                OUTPUT_FOLDER
            ).mkdir(
                exist_ok=True
            )

            report = self.generate_report()

            with open(

                f"{OUTPUT_FOLDER}/performance_report.txt",

                "w",

                encoding="utf-8"

            ) as f:

                f.write(report)

        return self.metrics    
        # =====================================================
    # Generate Report
    # =====================================================

    def generate_report(self) -> str:

        m = self.metrics

        report = f"""
============================================================
QUANTEDGE PERFORMANCE REPORT
============================================================

Initial Capital : ${m['initial_capital']:,.2f}
Final Capital   : ${m['final_capital']:,.2f}

Net Profit      : ${m['net_profit']:,.2f}
Return (%)      : {m['return_pct']:.2f}%

------------------------------------------------------------

Total Trades : {m['total_trades']}

Wins         : {m['wins']}
Losses       : {m['losses']}

Win Rate     : {m['win_rate']:.2f}%

Average RR   : {m['avg_rr']:.2f}

Gross Profit : {m['gross_profit']:.2f}R
Gross Loss   : {m['gross_loss']:.2f}R

Profit Factor: {m['profit_factor']:.2f}

Net R        : {m['net_r']:.2f}R

Max Win Streak  : {m['max_win_streak']}
Max Loss Streak : {m['max_loss_streak']}

Expectancy   : {m['expectancy']:.2f}R

============================================================
"""

        return report

    # =====================================================
    # Report
    # =====================================================

    def report(self):

        print(
            self.generate_report()
        )

    # =====================================================
    # Summary
    # =====================================================

    def summary(self):

        m = self.metrics

        print("=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)

        print(
            f"Trades        : {m['total_trades']}"
        )

        print(
            f"Win Rate      : {m['win_rate']:.2f}%"
        )

        print(
            f"Profit Factor : {m['profit_factor']:.2f}"
        )

        print(
            f"Net R         : {m['net_r']:.2f}"
        )

        print(
            f"Return        : {m['return_pct']:.2f}%"
        )

        print("=" * 60)


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from config import OUTPUT_FOLDER

    from analytics.equity_curve_v1 import (
        EquityCurve
    )

    print("=" * 60)
    print("QUANTEDGE PERFORMANCE ANALYZER")
    print("=" * 60)

    trades = pd.read_csv(

        f"{OUTPUT_FOLDER}/backtest_results_v1.csv"

    )

    print(
        f"Trades Loaded : {len(trades):,}"
    )

    curve = EquityCurve()

    equity_curve = curve.run(trades)

    analyzer = PerformanceAnalyzer()

    analyzer.run(

        trades,

        equity_curve,

        save_output=True

    )

    analyzer.report()

    analyzer.summary()

    print("\nValidation Complete")

    print("=" * 60)