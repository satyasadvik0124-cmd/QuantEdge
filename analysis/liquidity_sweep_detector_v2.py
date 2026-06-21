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
# LOAD DATA
# ==================================

price_df = pd.read_csv(
    f"../data/{PAIR}_{TIMEFRAME}.csv"
)

liquidity_df = pd.read_csv(
    "../outputs/liquidity_v2.csv"
)

price_df["time"] = pd.to_datetime(
    price_df["time"]
)

liquidity_df["time"] = pd.to_datetime(
    liquidity_df["time"]
)

# ==================================
# SWEEP DETECTION
# ==================================

sweeps = []

bullish_sweeps = 0
bearish_sweeps = 0

for _, level in liquidity_df.iterrows():

    liquidity_time = level["time"]
    liquidity_price = level["price"]
    liquidity_type = level["type"]

    future_candles = price_df[
        price_df["time"] > liquidity_time
    ]

    # ==========================
    # EQH -> BSL Sweep
    # ==========================

    if liquidity_type == "EQH":

        for _, candle in future_candles.iterrows():

            if (
                candle["high"] > liquidity_price
                and candle["close"] < liquidity_price
            ):

                sweeps.append({
                    "time": candle["time"],
                    "type": "BSL_SWEEP",
                    "price": liquidity_price
                })

                bearish_sweeps += 1
                break

    # ==========================
    # EQL -> SSL Sweep
    # ==========================

    elif liquidity_type == "EQL":

        for _, candle in future_candles.iterrows():

            if (
                candle["low"] < liquidity_price
                and candle["close"] > liquidity_price
            ):

                sweeps.append({
                    "time": candle["time"],
                    "type": "SSL_SWEEP",
                    "price": liquidity_price
                })

                bullish_sweeps += 1
                break

# ==================================
# SAVE
# ==================================

sweeps_df = pd.DataFrame(
    sweeps
)

if not sweeps_df.empty:

    sweeps_df = sweeps_df.drop_duplicates()

sweeps_df.to_csv(
    "../outputs/liquidity_sweeps_v2.csv",
    index=False
)

# ==================================
# REPORT
# ==================================

print("\n===== SWEEP REPORT =====\n")

print(
    f"Bullish Sweeps : "
    f"{bullish_sweeps:,}"
)

print(
    f"Bearish Sweeps : "
    f"{bearish_sweeps:,}"
)

print(
    f"Total Sweeps   : "
    f"{len(sweeps_df):,}"
)

if len(liquidity_df) > 0:

    print(
        f"Sweep Rate     : "
        f"{(len(sweeps_df)/len(liquidity_df))*100:.2f}%"
    )

print(
    "\nSaved:"
)

print(
    "../outputs/liquidity_sweeps_v2.csv"
)