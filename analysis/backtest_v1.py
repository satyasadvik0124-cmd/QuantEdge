import pandas as pd
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import PAIR, TIMEFRAME

print(f"\nUsing: {PAIR}_{TIMEFRAME}")

# ==================================
# LOAD PRICE DATA
# ==================================

price_df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

price_df["time"] = pd.to_datetime(
    price_df["time"]
)

# ==================================
# LOAD SIGNALS
# ==================================

signals_file = "../outputs/signals_v3.csv"

if not os.path.exists(signals_file):

    print("No signals file found.")
    exit()

try:

    signals_df = pd.read_csv(
        signals_file
    )

except pd.errors.EmptyDataError:

    print("No signals generated.")
    exit()

if signals_df.empty:

    print("No signals generated.")
    exit()

signals_df["signal_time"] = pd.to_datetime(
    signals_df["signal_time"]
)

results = []

print("\n===== BACKTESTER V1 =====\n")

# ==================================
# MAIN LOOP
# ==================================

for _, signal in signals_df.iterrows():

    signal_time = signal["signal_time"]

    direction = signal["direction"]

    entry = signal["entry"]
    sl = signal["sl"]
    tp = signal["tp"]

    signal_rows = price_df[
        price_df["time"] == signal_time
    ]

    if signal_rows.empty:
        continue

    start_idx = signal_rows.index[0]

    result = "OPEN"

    # ==================================
    # BUY
    # ==================================

    if direction == "BUY":

        for i in range(start_idx + 1, len(price_df)):

            candle = price_df.iloc[i]

            if candle["low"] <= sl:

                result = "LOSS"

                print(
                    f"LOSS | BUY | "
                    f"{signal_time}"
                )

                break

            if candle["high"] >= tp:

                result = "WIN"

                print(
                    f"WIN | BUY | "
                    f"{signal_time}"
                )

                break

    # ==================================
    # SELL
    # ==================================

    elif direction == "SELL":

        for i in range(start_idx + 1, len(price_df)):

            candle = price_df.iloc[i]

            if candle["high"] >= sl:

                result = "LOSS"

                print(
                    f"LOSS | SELL | "
                    f"{signal_time}"
                )

                break

            if candle["low"] <= tp:

                result = "WIN"

                print(
                    f"WIN | SELL | "
                    f"{signal_time}"
                )

                break

    # ==================================
    # SAVE RESULT
    # ==================================

    risk = abs(entry - sl)

    reward = abs(tp - entry)

    rr = round(
        reward / risk,
        2
    )

    results.append({
        "signal_time": signal_time,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "result": result,
        "rr": rr if result == "WIN" else -1
    })

# ==================================
# RESULTS DATAFRAME
# ==================================

results_df = pd.DataFrame(results)

results_df.to_csv(
    "../outputs/backtest_results_v1.csv",
    index=False
)

# ==================================
# STATS
# ==================================

wins = len(
    results_df[
        results_df["result"] == "WIN"
    ]
)

losses = len(
    results_df[
        results_df["result"] == "LOSS"
    ]
)

open_trades = len(
    results_df[
        results_df["result"] == "OPEN"
    ]
)

total = len(results_df)

win_rate = 0

if total > 0:

    win_rate = (
        wins / total
    ) * 100

# ==================================
# SUMMARY
# ==================================

print("\n===== SUMMARY =====")

print("Trades      :", total)
print("Wins        :", wins)
print("Losses      :", losses)
print("Open Trades :", open_trades)

print(
    "Win Rate    :",
    round(win_rate, 2),
    "%"
)

print(
    "\nSaved: ../outputs/backtest_results_v1.csv"
)