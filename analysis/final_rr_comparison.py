
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs" / "ml"

FILES = {
    "Original V1": ROOT / "outputs" / "backtest_results_v1.csv",
    "Entry-Touch": OUTPUT_DIR / "backtest_v1_vs_entry_touch_comparison.csv",
}

INITIAL_CAPITAL = 10_000
RISK_PERCENT = 1.0
RR = 4.0  # Your intended SMC risk-reward ratio: 1:4


def calculate_report(df, result_column):
    df = df.copy()
    df[result_column] = df[result_column].astype(str).str.upper()

    wins = (df[result_column] == "WIN").sum()
    losses = (df[result_column] == "LOSS").sum()
    open_trades = (df[result_column] == "OPEN").sum()
    no_entry = (df[result_column] == "NO_ENTRY").sum()

    resolved = wins + losses
    win_rate = wins / resolved * 100 if resolved else 0

    # Fixed-R calculation: each WIN earns +4R; each LOSS loses -1R.
    net_r = wins * RR - losses
    gross_profit_r = wins * RR
    gross_loss_r = losses
    profit_factor = (
        gross_profit_r / gross_loss_r if gross_loss_r else float("inf")
    )

    # Fixed 1% of initial capital per trade; does not compound.
    risk_amount = INITIAL_CAPITAL * RISK_PERCENT / 100
    net_profit = net_r * risk_amount
    final_balance = INITIAL_CAPITAL + net_profit

    return {
        "Total Signals": len(df),
        "Wins": int(wins),
        "Losses": int(losses),
        "Open": int(open_trades),
        "No Entry": int(no_entry),
        "Resolved Trades": int(resolved),
        "Win Rate (%)": round(win_rate, 2),
        "Assumed RR": f"1:{RR:g}",
        "Net R": round(net_r, 2),
        "Profit Factor": round(profit_factor, 2),
        "Initial Capital": INITIAL_CAPITAL,
        "Risk per Trade": f"{RISK_PERCENT:.1f}% of initial capital",
        "Net Profit": round(net_profit, 2),
        "Final Balance": round(final_balance, 2),
    }


def main():
    reports = []

    for name, path in FILES.items():
        if not path.exists():
            print(f"Skipping {name}: file not found: {path}")
            continue

        df = pd.read_csv(path)

        if name == "Original V1":
            result_column = "result"
        else:
            result_column = "alternative_result"

        if result_column not in df.columns:
            print(f"Skipping {name}: missing column {result_column}")
            continue

        report = calculate_report(df, result_column)
        report["Backtest"] = name
        reports.append(report)

    if not reports:
        print("No reports generated. Check the input file paths.")
        return

    report_df = pd.DataFrame(reports).set_index("Backtest")
    output_file = OUTPUT_DIR / "final_rr_comparison_report.csv"
    report_df.to_csv(output_file)

    print("\n===== FINAL RR PERFORMANCE REPORT =====\n")
    print(report_df.T.to_string())
    print(f"\nSaved report: {output_file}")
    print(
        "\nIMPORTANT: This uses assumed 1:4 RR and fixed 1% initial-capital "
        "risk per trade. It is a theoretical comparison, not an equity-curve "
        "backtest. The entry-touch scenario has different exit-check timing."
    )


if __name__ == "__main__":
    main()

