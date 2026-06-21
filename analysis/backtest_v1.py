import pandas as pd

# ==================================
# LOAD DATA
# ==================================

price_df = pd.read_csv("../data/EURUSD_M15.csv")
signals_df = pd.read_csv("../outputs/signals_v2.csv")

price_df["time"] = pd.to_datetime(price_df["time"])
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

    # ----------------------------------
    # Find signal candle index
    # ----------------------------------

    signal_rows = price_df[
        price_df["time"] == signal_time
    ]

    if signal_rows.empty:
        continue

    start_idx = signal_rows.index[0]

    result = "OPEN"

    # ==================================
    # BUY SIGNAL
    # ==================================

    if direction == "BUY":

        for i in range(start_idx + 1, len(price_df)):

            candle = price_df.iloc[i]

            # Stop Loss hit
            if candle["low"] <= sl:

                result = "LOSS"

                print(
                    f"LOSS | BUY | "
                    f"{signal_time}"
                )

                break

            # Take Profit hit
            if candle["high"] >= tp:

                result = "WIN"

                print(
                    f"WIN | BUY | "
                    f"{signal_time}"
                )

                break

    # ==================================
    # SELL SIGNAL
    # ==================================

    elif direction == "SELL":

        for i in range(start_idx + 1, len(price_df)):

            candle = price_df.iloc[i]

            # Stop Loss hit
            if candle["high"] >= sl:

                result = "LOSS"

                print(
                    f"LOSS | SELL | "
                    f"{signal_time}"
                )

                break

            # Take Profit hit
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

    results.append({
        "signal_time": signal_time,
        "direction": direction,

        "entry": entry,
        "sl": sl,
        "tp": tp,

        "result": result
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
    win_rate = (wins / total) * 100

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