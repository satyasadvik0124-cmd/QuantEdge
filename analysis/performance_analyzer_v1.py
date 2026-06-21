import pandas as pd
import os

# ==========================
# LOAD BACKTEST RESULTS
# ==========================

FILE_PATH = "../outputs/backtest_results_v1.csv"

if not os.path.exists(FILE_PATH):
    print(f"File not found: {FILE_PATH}")
    exit()

df = pd.read_csv(FILE_PATH)

# ==========================
# LOAD EQUITY CURVE
# ==========================

EQUITY_FILE = "../outputs/equity_curve.csv"

if not os.path.exists(EQUITY_FILE):
    print(f"File not found: {EQUITY_FILE}")
    exit()

equity_df = pd.read_csv(EQUITY_FILE)

# ==========================
# DEBUG INFO
# ==========================

print("\n===== COLUMNS =====")
print(df.columns.tolist())

print("\n===== FIRST 5 ROWS =====")
print(df.head())

# ==========================
# FIND RESULT COLUMN
# ==========================

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
    if col in df.columns:
        result_col = col
        break

if result_col is None:
    print("\n❌ Could not find result column.")
    print("Available columns:", df.columns.tolist())
    exit()

# ==========================
# FIND RR COLUMN
# ==========================

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
    if col in df.columns:
        rr_col = col
        break

if rr_col is None:
    print("\n❌ Could not find RR column.")
    print("Available columns:", df.columns.tolist())
    exit()

# ==========================
# BASIC METRICS
# ==========================

total_trades = len(df)

wins = len(
    df[
        df[result_col]
        .astype(str)
        .str.upper()
        .isin(["WIN", "TP", "PROFIT"])
    ]
)

losses = len(
    df[
        df[result_col]
        .astype(str)
        .str.upper()
        .isin(["LOSS", "SL", "LOSE"])
    ]
)

win_rate = (
    wins / total_trades * 100
    if total_trades > 0
    else 0
)

# ==========================
# RR METRICS
# ==========================

avg_rr = df[rr_col].mean()

gross_profit = (
    df[df[rr_col] > 0][rr_col]
    .sum()
)

gross_loss = abs(
    df[df[rr_col] < 0][rr_col]
    .sum()
)

profit_factor = (
    gross_profit / gross_loss
    if gross_loss > 0
    else float("inf")
)

net_r = df[rr_col].sum()

# ==========================
# STREAKS
# ==========================

max_win_streak = 0
max_loss_streak = 0

current_win = 0
current_loss = 0

for result in df[result_col]:

    result = str(result).upper()

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

# ==========================
# EXPECTANCY
# ==========================

expectancy = (
    net_r / total_trades
    if total_trades > 0
    else 0
)

# ==========================
# CAPITAL METRICS
# ==========================

INITIAL_CAPITAL = 10000

final_capital = (
    equity_df.iloc[-1]["equity"]
)

net_profit = (
    final_capital
    - INITIAL_CAPITAL
)

return_pct = (
    net_profit
    / INITIAL_CAPITAL
) * 100

# ==========================
# REPORT
# ==========================

report = f"""
=================================
QUANTEDGE PERFORMANCE REPORT
=================================

Initial Capital : ${INITIAL_CAPITAL:,.2f}
Final Capital   : ${final_capital:,.2f}

Net Profit      : ${net_profit:,.2f}
Return (%)      : {return_pct:.2f}%

---------------------------------

Total Trades : {total_trades}

Wins         : {wins}
Losses       : {losses}

Win Rate     : {win_rate:.2f}%

Average RR   : {avg_rr:.2f}

Gross Profit : {gross_profit:.2f}R
Gross Loss   : {gross_loss:.2f}R

Profit Factor: {profit_factor:.2f}

Net R        : {net_r:.2f}R

Max Win Streak  : {max_win_streak}
Max Loss Streak : {max_loss_streak}

Expectancy   : {expectancy:.2f}R

=================================
"""

print(report)

# ==========================
# SAVE REPORT
# ==========================

with open(
    "../outputs/performance_report.txt",
    "w",
    encoding="utf-8"
) as f:
    f.write(report)

print("✅ Performance report saved.")